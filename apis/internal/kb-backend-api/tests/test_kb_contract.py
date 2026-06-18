from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.domain.entities.kb_article import ArticleVisibility, KBArticle, KBCategory
from app.events import publishers
from app.infrastructure import database
from app.infrastructure.persistence.kb_repository import KBRepository
from app.middleware.auth import get_current_user, settings
from app.presentation.routes import kb_routes
from app.presentation.schemas import kb_schemas


USER = {"user_id": "user-1", "email": "kb@example.com", "tenant_id": "tenant-1"}
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def stamp(entity):
    entity.created_at = NOW
    entity.updated_at = NOW
    entity.version = 1
    entity.is_deleted = False
    entity.deleted_at = None
    entity.deleted_by = None
    return entity


def make_category(category_id="cat-1", **overrides):
    category = KBCategory(
        id=category_id,
        name="Getting Started",
        slug="getting-started",
        description="Start here",
        icon="book",
        color="#336699",
        sort_order=1,
        article_count=1,
        tenant_id="tenant-1",
        created_by="kb@example.com",
    )
    for key, value in overrides.items():
        setattr(category, key, value)
    return stamp(category)


def make_article(article_id="article-1", **overrides):
    article = KBArticle(
        id=article_id,
        title="Welcome",
        slug="welcome",
        excerpt="Quick start",
        content="Read this first.",
        category_id="cat-1",
        tags=["start"],
        visibility=ArticleVisibility.SHARED,
        required_module=None,
        required_role=None,
        author_name="Ada",
        author_role="Editor",
        author_avatar=None,
        read_time_minutes=4,
        view_count=7,
        helpful_yes=2,
        helpful_no=1,
        is_published=True,
        is_featured=True,
        tenant_id="tenant-1",
        created_by="kb@example.com",
    )
    article.category = make_category()
    for key, value in overrides.items():
        setattr(article, key, value)
    return stamp(article)


class FakeQuery:
    def __init__(self, items=None, scalar_value=5):
        self.items = list(items or [])
        self.scalar_value = scalar_value

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def offset(self, skip):
        self.items = self.items[skip:]
        return self

    def limit(self, limit):
        self.items = self.items[:limit]
        return self

    def first(self):
        return self.items[0] if self.items else None

    def all(self):
        return self.items

    def count(self):
        return len(self.items)

    def scalar(self):
        return self.scalar_value


class FakeDB:
    def __init__(self):
        self.category = make_category()
        self.article = make_article()
        self.storage = {KBCategory: [self.category], KBArticle: [self.article]}
        self.added = []
        self.deleted = []
        self.commits = 0
        self.refreshes = 0

    def query(self, entity):
        if entity in self.storage:
            return FakeQuery(self.storage[entity])
        return FakeQuery(scalar_value=5)

    def add(self, entity):
        self.added.append(entity)
        if not getattr(entity, "id", None):
            entity.id = f"{entity.__class__.__name__.lower()}-{len(self.added)}"
        if isinstance(entity, KBCategory):
            entity.article_count = entity.article_count if entity.article_count is not None else 0
            entity.sort_order = entity.sort_order if entity.sort_order is not None else 0
        entity.created_at = getattr(entity, "created_at", None) or NOW
        entity.updated_at = getattr(entity, "updated_at", None) or NOW
        entity.version = getattr(entity, "version", None) or 1
        entity.is_deleted = getattr(entity, "is_deleted", None) or False
        self.storage.setdefault(entity.__class__, []).append(entity)

    def commit(self):
        self.commits += 1

    def refresh(self, entity):
        self.refreshes += 1
        if not getattr(entity, "id", None):
            entity.id = f"{entity.__class__.__name__.lower()}-{self.refreshes}"
        if isinstance(entity, KBCategory):
            entity.article_count = entity.article_count if entity.article_count is not None else 0
            entity.sort_order = entity.sort_order if entity.sort_order is not None else 0
        entity.created_at = getattr(entity, "created_at", None) or NOW
        entity.updated_at = getattr(entity, "updated_at", None) or NOW
        entity.version = getattr(entity, "version", None) or 1
        entity.is_deleted = getattr(entity, "is_deleted", None) or False

    def close(self):
        return None


class FakeKBRepository:
    def __init__(self, db):
        self.db = db
        self.category = make_category()
        self.article = make_article()
        self.count_updates = []

    def list_categories(self, tenant_id):
        return [self.category]

    def create_category(self, category):
        category.id = "cat-new"
        category.article_count = category.article_count if category.article_count is not None else 0
        category.sort_order = category.sort_order if category.sort_order is not None else 0
        return stamp(category)

    def get_category_by_id(self, category_id, tenant_id):
        return self.category if category_id == "cat-1" else None

    def update_category(self, category):
        category.version += 1
        return category

    def list_articles(self, tenant_id, skip=0, limit=20, search=None, category_id=None, visibility=None):
        return [self.article]

    def count_articles(self, tenant_id, category_id=None, visibility=None):
        return 1

    def popular_articles(self, tenant_id, limit=10):
        return [self.article]

    def create_article(self, article):
        article.id = "article-new"
        article.view_count = article.view_count or 0
        article.helpful_yes = article.helpful_yes or 0
        article.helpful_no = article.helpful_no or 0
        return stamp(article)

    def get_article_by_slug(self, slug, tenant_id):
        return self.article if slug == "welcome" else None

    def get_article_by_id(self, article_id, tenant_id):
        return self.article if article_id == "article-1" else None

    def increment_view_count(self, article):
        article.view_count += 1

    def update_article(self, article):
        article.version += 1
        return article

    def update_category_article_count(self, category_id, tenant_id):
        self.count_updates.append((category_id, tenant_id))

    def soft_delete_article(self, article, deleted_by):
        article.is_deleted = True
        article.deleted_by = deleted_by
        return article

    def record_feedback(self, article, helpful):
        if helpful:
            article.helpful_yes += 1
        else:
            article.helpful_no += 1

    def get_stats(self, tenant_id):
        return {
            "total_articles": 1,
            "published_articles": 1,
            "total_categories": 1,
            "total_views": 8,
            "avg_helpfulness": 66.7,
        }


class EmptyKBRepository(FakeKBRepository):
    def get_category_by_id(self, category_id, tenant_id):
        return None

    def get_article_by_slug(self, slug, tenant_id):
        return None

    def get_article_by_id(self, article_id, tenant_id):
        return None


@pytest.fixture()
def repo():
    return FakeKBRepository(FakeDB())


@pytest.fixture()
def client(monkeypatch, repo):
    async def noop_publish(*args, **kwargs):
        return None

    monkeypatch.setattr(kb_routes, "KBRepository", lambda db: repo)
    monkeypatch.setattr(kb_routes, "publish_article_created", noop_publish)
    monkeypatch.setattr(kb_routes, "publish_article_updated", noop_publish)
    monkeypatch.setattr(kb_routes, "publish_article_deleted", noop_publish)
    main.app.dependency_overrides[kb_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[kb_routes.get_db] = lambda: FakeDB()
    test_client = TestClient(main.app)
    yield test_client
    test_client.close()
    main.app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers():
    token = jwt.encode(
        {"sub": "user-1", "email": "kb@example.com", "tenant_id": "tenant-1"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def test_monitoring_endpoints(client):
    for path in ["/health", "/readiness", "/liveness", "/startup", "/metrics"]:
        response = client.get(path)
        assert response.status_code == 200
    assert "dependencies" in client.get("/health").json()
    assert "cde_api_info" in client.get("/metrics").text


def test_auth_dependency_accepts_and_rejects_tokens(auth_headers):
    credentials = type("Credentials", (), {"credentials": auth_headers["Authorization"].split(" ", 1)[1]})()
    assert get_current_user(credentials)["tenant_id"] == "tenant-1"

    invalid = type("Credentials", (), {"credentials": "not-a-token"})()
    with pytest.raises(Exception) as invalid_token:
        get_current_user(invalid)
    assert getattr(invalid_token.value, "status_code", None) == 401

    no_sub = jwt.encode({"email": "kb@example.com"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(Exception) as missing_sub:
        get_current_user(type("Credentials", (), {"credentials": no_sub})())
    assert getattr(missing_sub.value, "status_code", None) == 401


def test_category_routes(client, monkeypatch):
    assert client.get("/api/v1/kb/categories").json()["total"] == 1
    created = client.post(
        "/api/v1/kb/categories",
        json={"name": "FAQ", "slug": "faq", "description": "Questions"},
    )
    assert created.status_code == 201
    assert created.json()["id"] == "cat-new"
    assert client.get("/api/v1/kb/categories/cat-1").json()["slug"] == "getting-started"
    assert client.patch("/api/v1/kb/categories/cat-1", json={"name": "Updated"}).json()["name"] == "Updated"

    monkeypatch.setattr(kb_routes, "KBRepository", lambda db: EmptyKBRepository(db))
    assert client.get("/api/v1/kb/categories/missing").status_code == 404
    assert client.patch("/api/v1/kb/categories/missing", json={"name": "Updated"}).status_code == 404


def test_article_routes(client, repo, monkeypatch):
    listed = client.get("/api/v1/kb/articles", params={"search": "Welcome", "category_id": "cat-1", "visibility": "shared"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert client.get("/api/v1/kb/articles/popular").json()[0]["id"] == "article-1"
    created = client.post(
        "/api/v1/kb/articles",
        json={
            "title": "Install",
            "slug": "install",
            "content": "Steps",
            "category_id": "cat-1",
            "is_published": True,
        },
    )
    assert created.status_code == 201
    assert created.json()["id"] == "article-new"
    assert client.get("/api/v1/kb/articles/welcome").json()["view_count"] == 8
    assert client.get("/api/v1/kb/articles/article-1").json()["id"] == "article-1"
    updated = client.patch("/api/v1/kb/articles/article-1", json={"category_id": "cat-2", "title": "Updated"})
    assert updated.status_code == 200
    assert ("cat-1", "tenant-1") in repo.count_updates
    assert ("cat-2", "tenant-1") in repo.count_updates
    assert client.post("/api/v1/kb/articles/article-1/feedback", json={"helpful": True}).json()["helpful_yes"] == 3
    assert client.delete("/api/v1/kb/articles/article-1").status_code == 204
    assert client.get("/api/v1/kb/stats").json()["total_articles"] == 1

    monkeypatch.setattr(kb_routes, "KBRepository", lambda db: EmptyKBRepository(db))
    assert client.get("/api/v1/kb/articles/missing").status_code == 404
    assert client.patch("/api/v1/kb/articles/missing", json={"title": "Nope"}).status_code == 404
    assert client.delete("/api/v1/kb/articles/missing").status_code == 404
    assert client.post("/api/v1/kb/articles/missing/feedback", json={"helpful": False}).status_code == 404


@pytest.mark.asyncio
async def test_publishers_emit_kb_domain_events(monkeypatch):
    published = []

    async def fake_publish(event):
        published.append(event)

    monkeypatch.setattr(publishers.event_bus, "publish", fake_publish)
    await publishers.publish_article_created("article-1", {"title": "Welcome"})
    await publishers.publish_article_updated("article-1", {"fields": ["title"]})
    await publishers.publish_article_deleted("article-1")
    assert [event["type"] for event in published] == [
        "kb.article.created",
        "kb.article.updated",
        "kb.article.deleted",
    ]


def test_database_facade_and_schema_contracts(monkeypatch):
    monkeypatch.setattr(database, "create_db_engine", lambda api_name: f"engine:{api_name}")
    monkeypatch.setattr(database, "create_session_factory", lambda api_name: f"factory:{api_name}")
    database.init("kb-backend")
    assert database.get_engine() == "engine:kb-backend"
    assert database.get_session_factory() == "factory:kb-backend"

    assert kb_schemas.CategoryResponse.model_validate(make_category()).id == "cat-1"
    assert kb_schemas.ArticleResponse.model_validate(make_article()).id == "article-1"
    assert kb_schemas.ArticleSummaryResponse.model_validate(make_article()).slug == "welcome"
    assert kb_schemas.CategoryListResponse(items=[make_category()], total=1).total == 1
    assert kb_schemas.ArticleListResponse(items=[make_article()], total=1).limit == 20
    assert kb_schemas.FeedbackRequest(helpful=True).helpful is True
    assert kb_schemas.KBStatsResponse(
        total_articles=1,
        published_articles=1,
        total_categories=1,
        total_views=8,
        avg_helpfulness=66.7,
    ).total_views == 8


def test_repository_methods_cover_persistence_paths():
    session = FakeDB()
    repository = KBRepository(session)

    assert repository.create_category(make_category("cat-new")).id == "cat-new"
    assert repository.list_categories("tenant-1")[0].id == "cat-1"
    assert repository.get_category_by_id("cat-1", "tenant-1").id == "cat-1"
    assert repository.update_category(session.category).version == 2
    repository.update_category_article_count("cat-1", "tenant-1")
    assert session.category.article_count >= 1

    assert repository.create_article(make_article("article-new")).id == "article-new"
    assert repository.get_article_by_id("article-1", "tenant-1").id == "article-1"
    assert repository.get_article_by_slug("welcome", "tenant-1").id == "article-1"
    assert len(repository.list_articles("tenant-1", search="Wel", category_id="cat-1", visibility="shared")) >= 1
    assert repository.count_articles("tenant-1", category_id="cat-1", visibility="shared") >= 1
    assert repository.popular_articles("tenant-1", 10)[0].id == "article-1"
    repository.increment_view_count(session.article)
    assert session.article.view_count == 8
    repository.record_feedback(session.article, True)
    repository.record_feedback(session.article, False)
    assert session.article.helpful_yes == 3
    assert session.article.helpful_no == 2
    assert repository.update_article(session.article).version == 2
    assert repository.soft_delete_article(session.article, "kb@example.com").is_deleted is True
    stats = repository.get_stats("tenant-1")
    assert stats["total_articles"] >= 1
    assert stats["avg_helpfulness"] == 50.0


def test_python_package_contract_loads_runtime_components():
    from kb_backend_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (kb_routes,)
    assert contract.load_runtime_repository_classes() == (KBRepository,)
    assert contract.load_runtime_entity_classes() == (KBArticle, KBCategory, ArticleVisibility)
