from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from shared.database import connection as shared_db_connection

import main
from app.domain.entities.activity import Activity, ActivityPriority, ActivityStatus, ActivityType
from app.events import publishers
from app.infrastructure import database
from app.infrastructure.persistence.activity_repository import ActivityRepository
from app.middleware.auth import get_current_user, settings
from app.presentation.routes import activity_routes
from app.presentation.schemas import activity_schemas


USER = {"user_id": "user-1", "email": "user@example.com", "tenant_id": "tenant-1"}
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_activity(activity_id="activity-1", **overrides):
    activity = Activity(
        id=activity_id,
        subject="Follow up",
        description="Call the client",
        activity_type=ActivityType.CALL,
        priority=ActivityPriority.HIGH,
        status=ActivityStatus.PENDING,
        due_date=NOW,
        completed_at=None,
        organization_ids=["org-1"],
        contact_ids=["contact-1"],
        opportunity_ids=["opp-1"],
        assigned_to="user@example.com",
        owner_id="user-1",
        tenant_id="tenant-1",
        created_by="user@example.com",
        updated_by=None,
    )
    activity.created_at = NOW
    activity.updated_at = NOW
    activity.version = 1
    activity.is_deleted = False
    activity.deleted_at = None
    activity.deleted_by = None
    activity.deleted_reason = None
    for key, value in overrides.items():
        setattr(activity, key, value)
    return activity


class FakeActivityRepository:
    def __init__(self, db):
        self.db = db
        self.activities = {"activity-1": make_activity()}

    def create(self, activity):
        activity.id = "activity-new"
        activity.created_at = NOW
        activity.updated_at = NOW
        activity.version = 1
        activity.is_deleted = False
        self.activities[activity.id] = activity
        return activity

    def get_by_id(self, activity_id, tenant_id):
        activity = self.activities.get(activity_id)
        return activity if activity and activity.tenant_id == tenant_id and not activity.is_deleted else None

    def list_all(self, tenant_id, skip=0, limit=50, status=None):
        items = [a for a in self.activities.values() if a.tenant_id == tenant_id and not a.is_deleted]
        if status:
            items = [a for a in items if a.status == status or getattr(a.status, "value", a.status) == status]
        return items[skip : skip + limit]

    def count(self, tenant_id, status=None):
        return len(self.list_all(tenant_id, status=status))

    def update(self, activity):
        activity.updated_at = NOW
        activity.version = (activity.version or 0) + 1
        return activity

    def soft_delete(self, activity, deleted_by, reason=None):
        activity.is_deleted = True
        activity.deleted_at = NOW
        activity.deleted_by = deleted_by
        activity.deleted_reason = reason
        activity.version = (activity.version or 0) + 1
        return activity


class FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.refreshed = []

    def add(self, entity):
        self.added.append(entity)

    def commit(self):
        self.commits += 1

    def refresh(self, entity):
        self.refreshed.append(entity)


class FakeQuery:
    def __init__(self, result=None, results=None, count_value=1):
        self.result = result
        self.results = list(results or [])
        self.count_value = count_value

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def offset(self, skip):
        self.results = self.results[skip:]
        return self

    def limit(self, limit):
        self.results = self.results[:limit]
        return self

    def first(self):
        return self.result

    def all(self):
        return self.results

    def count(self):
        return self.count_value


class RepositorySession(FakeDB):
    def __init__(self):
        super().__init__()
        self.activity = make_activity()

    def query(self, entity):
        if entity is Activity:
            return FakeQuery(self.activity, [self.activity], 1)
        return FakeQuery()


@pytest.fixture()
def repo():
    return FakeActivityRepository(FakeDB())


@pytest.fixture()
def client(monkeypatch, repo):
    async def noop_publish(*args, **kwargs):
        return None

    monkeypatch.setattr(activity_routes, "ActivityRepository", lambda db: repo)
    monkeypatch.setattr(activity_routes, "publish_activity_created", noop_publish)
    monkeypatch.setattr(activity_routes, "publish_activity_updated", noop_publish)
    main.app.dependency_overrides[activity_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[activity_routes.get_db] = lambda: FakeDB()
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers():
    token = jwt.encode(
        {"sub": "user-1", "email": "user@example.com", "tenant_id": "tenant-1"},
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


def test_activity_crud_routes(client):
    created = client.post(
        "/api/v1/activities",
        json={"subject": "New activity", "activity_type": "TASK", "status": "PENDING"},
    )
    assert created.status_code == 201
    assert created.json()["id"] == "activity-new"

    listed = client.get("/api/v1/activities", params={"status": "PENDING"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert client.get("/api/v1/activities/activity-1").json()["id"] == "activity-1"
    assert client.get("/api/v1/activities/missing").status_code == 404
    assert client.patch("/api/v1/activities/activity-1", json={"subject": "Updated"}).json()["subject"] == "Updated"
    assert client.patch("/api/v1/activities/missing", json={"subject": "Updated"}).status_code == 404
    assert client.delete("/api/v1/activities/activity-1").status_code == 204
    assert client.delete("/api/v1/activities/missing").status_code == 404


def test_auth_dependency_accepts_and_rejects_tokens(auth_headers):
    credentials = type("Credentials", (), {"credentials": auth_headers["Authorization"].split(" ", 1)[1]})()
    assert get_current_user(credentials)["tenant_id"] == "tenant-1"

    invalid = type("Credentials", (), {"credentials": "not-a-token"})()
    with pytest.raises(Exception) as invalid_token:
        get_current_user(invalid)
    assert getattr(invalid_token.value, "status_code", None) == 401

    no_sub = jwt.encode({"email": "user@example.com"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(Exception) as missing_sub:
        get_current_user(type("Credentials", (), {"credentials": no_sub})())
    assert getattr(missing_sub.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_publishers_emit_domain_events(monkeypatch):
    published = []

    async def fake_publish(event):
        published.append(event)

    monkeypatch.setattr(publishers.event_bus, "publish", fake_publish)
    await publishers.publish_activity_created("activity-1", {"subject": "Follow up"})
    await publishers.publish_activity_updated("activity-1", {"subject": "Updated"})
    assert [event.event_type for event in published] == ["activity.created", "activity.updated"]
    assert [event.payload["entity_id"] for event in published] == ["activity-1", "activity-1"]


def test_repository_methods_cover_persistence_paths():
    session = RepositorySession()
    repository = ActivityRepository(session)

    assert repository.create(make_activity("activity-new")).id == "activity-new"
    assert repository.get_by_id("activity-1", "tenant-1").id == "activity-1"
    assert repository.list_all("tenant-1", status="PENDING")[0].id == "activity-1"
    assert repository.count("tenant-1", status="PENDING") == 1
    assert repository.update(session.activity).version == 2
    deleted = repository.soft_delete(session.activity, "user@example.com", reason="duplicate")
    assert deleted.is_deleted is True
    assert deleted.deleted_reason == "duplicate"
    assert session.commits >= 1


def test_database_facade_and_schema_contracts(monkeypatch):
    monkeypatch.setattr(database, "create_db_engine", lambda api_name: f"engine:{api_name}")
    monkeypatch.setattr(database, "create_session_factory", lambda api_name: f"factory:{api_name}")
    database.init("activity-backend")
    assert database.get_engine() == "engine:activity-backend"
    assert database.get_session_factory() == "factory:activity-backend"

    assert activity_schemas.ActivityCreate(subject="Task").activity_type == "TASK"
    assert activity_schemas.ActivityUpdate(subject="Updated").subject == "Updated"
    response = activity_schemas.ActivityResponse.model_validate(make_activity())
    assert response.id == "activity-1"
    assert activity_schemas.ActivityListResponse(items=[response], total=1, skip=0, limit=50).total == 1


def test_shared_database_engine_uses_pgbouncer_safe_options(monkeypatch):
    captured = {}

    def fake_create_engine(database_url, **kwargs):
        captured["database_url"] = database_url
        captured["kwargs"] = kwargs
        return "engine"

    shared_db_connection._engines.clear()
    shared_db_connection._session_factories.clear()
    monkeypatch.setattr(shared_db_connection, "create_engine", fake_create_engine)
    monkeypatch.setattr(
        shared_db_connection,
        "get_settings",
        lambda api_name: SimpleNamespace(
            database_url="postgresql+psycopg://user:pass@pgbouncer:5432/app"
        ),
    )
    monkeypatch.setenv("DB_POOL_SIZE", "99")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "99")

    assert shared_db_connection.create_db_engine("activity-backend-api") == "engine"
    assert captured["kwargs"]["pool_size"] == 5
    assert captured["kwargs"]["max_overflow"] == 5
    assert captured["kwargs"]["pool_pre_ping"] is True
    assert captured["kwargs"]["pool_recycle"] == 300
    assert captured["kwargs"]["connect_args"] == {"prepare_threshold": None}
    assert shared_db_connection._connect_args_for_database_url(
        "postgresql+psycopg2://user:pass@pgbouncer:5432/app"
    ) == {}
    assert shared_db_connection._connect_args_for_database_url("sqlite:///local.db") == {
        "check_same_thread": False
    }
    monkeypatch.setenv("DB_POOL_SIZE", "-10")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "not-an-int")
    assert shared_db_connection._bounded_int_from_env("DB_POOL_SIZE", 3, 1, 5) == 1
    assert shared_db_connection._bounded_int_from_env("DB_MAX_OVERFLOW", 5, 0, 5) == 5


def test_python_package_contract_loads_runtime_components():
    from activity_backend_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (activity_routes,)
    assert contract.load_runtime_repository_classes() == (ActivityRepository,)
    assert contract.load_runtime_entity_classes() == (
        Activity,
        ActivityType,
        ActivityPriority,
        ActivityStatus,
    )
