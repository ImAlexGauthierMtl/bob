import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.infrastructure.clients.kb_client import KBClient as RuntimeKBClient
from app.middleware.auth import get_current_user as runtime_get_current_user
from app.middleware.auth import settings as runtime_settings
from app.presentation.routes import kb_routes as runtime_kb_routes


class FakeKBClient:
    async def list_categories(self, forward_headers=None):
        return [{"id": "cat-1", "name": "General"}]

    async def create_category(self, data, forward_headers=None):
        return {"id": "cat-2", **data}

    async def get_category(self, category_id, forward_headers=None):
        if category_id == "missing":
            return None
        return {"id": category_id, "name": "General"}

    async def update_category(self, category_id, data, forward_headers=None):
        return {"id": category_id, **data}

    async def list_articles(self, skip=0, limit=20, search=None, category_id=None, visibility=None, forward_headers=None):
        return {
            "items": [{"id": "article-1", "title": search or "Welcome"}],
            "skip": skip,
            "limit": limit,
            "category_id": category_id,
            "visibility": visibility,
        }

    async def popular_articles(self, limit=10, forward_headers=None):
        return [{"id": "article-1", "score": limit}]

    async def create_article(self, data, forward_headers=None):
        return {"id": "article-2", **data}

    async def get_article(self, slug, forward_headers=None):
        if slug == "missing":
            return None
        return {"id": "article-1", "slug": slug}

    async def update_article(self, article_id, data, forward_headers=None):
        return {"id": article_id, **data}

    async def delete_article(self, article_id, forward_headers=None):
        return True

    async def article_feedback(self, article_id, data, forward_headers=None):
        return {"article_id": article_id, **data}

    async def get_stats(self, forward_headers=None):
        return {"articles": 4, "categories": 2}


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload or {}
        self.status_code = status_code
        self.raised = False

    def json(self):
        return self._payload

    def raise_for_status(self):
        self.raised = True


class FakeServiceClient:
    def __init__(self):
        self.calls = []

    async def get(self, path, params=None, forward_headers=None):
        self.calls.append(("get", path, params, forward_headers))
        if path.endswith("/missing"):
            return FakeResponse(status_code=404)
        return FakeResponse({"path": path, "params": params})

    async def post(self, path, json=None, forward_headers=None):
        self.calls.append(("post", path, json, forward_headers))
        return FakeResponse({"path": path, "json": json}, status_code=201)

    async def patch(self, path, json=None, forward_headers=None):
        self.calls.append(("patch", path, json, forward_headers))
        return FakeResponse({"path": path, "json": json})

    async def delete(self, path, forward_headers=None):
        self.calls.append(("delete", path, None, forward_headers))
        return FakeResponse(status_code=204)


@pytest.fixture()
def client(monkeypatch):
    app = main.app
    routes = runtime_kb_routes
    app.dependency_overrides[routes.get_current_user] = lambda: {"user_id": "user-1"}
    monkeypatch.setattr(routes, "kb_client", FakeKBClient())
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_monitoring_endpoints(client):
    for path in ["/health", "/readiness", "/liveness", "/startup", "/metrics"]:
        response = client.get(path)
        assert response.status_code == 200
    assert "dependencies" in client.get("/health").json()
    assert "cde_api_info" in client.get("/metrics").text


def test_category_routes(client):
    assert client.get("/kb/categories").json()[0]["id"] == "cat-1"
    assert client.post("/kb/categories", json={"name": "Docs"}).status_code == 201
    assert client.get("/kb/categories/cat-1").json()["id"] == "cat-1"
    assert client.get("/kb/categories/missing").status_code == 404
    assert client.patch("/kb/categories/cat-1", json={"name": "Updated"}).json()["name"] == "Updated"


def test_article_routes(client):
    listed = client.get(
        "/kb/articles",
        params={"skip": 1, "limit": 5, "search": "onboarding", "category_id": "cat-1", "visibility": "public"},
    ).json()
    assert listed["skip"] == 1
    assert client.get("/kb/articles/popular", params={"limit": 3}).json()[0]["score"] == 3
    assert client.post("/kb/articles", json={"title": "New"}).status_code == 201
    assert client.get("/kb/articles/welcome").json()["slug"] == "welcome"
    assert client.get("/kb/articles/missing").status_code == 404
    assert client.patch("/kb/articles/article-1", json={"title": "Updated"}).json()["title"] == "Updated"
    assert client.delete("/kb/articles/article-1").status_code == 204


def test_feedback_and_stats_routes(client):
    feedback = client.post("/kb/articles/article-1/feedback", json={"rating": 5}).json()
    assert feedback["article_id"] == "article-1"
    assert client.get("/kb/stats").json()["articles"] == 4


def test_auth_dependency_accepts_valid_jwt():
    token = jwt.encode(
        {"sub": "user-1", "email": "user@example.com", "tenant_id": "tenant-1"},
        runtime_settings.jwt_secret_key,
        algorithm=runtime_settings.jwt_algorithm,
    )
    credentials = type("Credentials", (), {"credentials": token})()
    user = runtime_get_current_user(credentials)
    assert user == {"user_id": "user-1", "email": "user@example.com", "tenant_id": "tenant-1"}


def test_auth_dependency_rejects_invalid_jwt():
    credentials = type("Credentials", (), {"credentials": "not-a-token"})()
    with pytest.raises(Exception) as exc_info:
        runtime_get_current_user(credentials)
    assert getattr(exc_info.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_backend_client_methods_cover_paths(monkeypatch):
    fake_service_client = FakeServiceClient()
    monkeypatch.setattr("app.infrastructure.clients.kb_client.create_service_client", lambda name: fake_service_client)
    client = RuntimeKBClient()

    assert await client.list_categories() == {"path": "/api/v1/kb/categories", "params": None}
    assert (await client.create_category({"name": "Docs"}))["json"]["name"] == "Docs"
    assert await client.get_category("missing") is None
    assert (await client.get_category("cat-1"))["path"].endswith("/cat-1")
    assert (await client.update_category("cat-1", {"name": "Updated"}))["json"]["name"] == "Updated"

    articles = await client.list_articles(1, 5, "search", "cat-1", "public")
    assert articles["params"] == {
        "skip": "1",
        "limit": "5",
        "search": "search",
        "category_id": "cat-1",
        "visibility": "public",
    }
    assert (await client.popular_articles(3))["params"] == {"limit": "3"}
    assert (await client.create_article({"title": "New"}))["json"]["title"] == "New"
    assert await client.get_article("missing") is None
    assert (await client.get_article("welcome"))["path"].endswith("/welcome")
    assert (await client.update_article("article-1", {"title": "Updated"}))["json"]["title"] == "Updated"
    assert await client.delete_article("article-1") is True
    assert (await client.article_feedback("article-1", {"rating": 5}))["json"]["rating"] == 5
    assert (await client.get_stats())["path"] == "/api/v1/kb/stats"


def test_python_package_contract_loads_runtime_components():
    from kb_b4f_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() is runtime_kb_routes
    assert contract.load_runtime_client_class() is RuntimeKBClient
