from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.infrastructure.persistence.models.contact import Contact, ContactStatus
from app.events import publishers
from app.infrastructure import database
from app.infrastructure.persistence.contact_repository import ContactRepository
from app.middleware.auth import get_current_user, settings
from app.presentation.routes import contact_routes
from app.presentation.schemas import contact_schemas


USER = {"user_id": "user-1", "email": "user@example.com", "tenant_id": "tenant-1"}
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_contact(contact_id="contact-1", **overrides):
    contact = Contact(
        id=contact_id,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone="555-0100",
        mobile="555-0101",
        job_title="Architect",
        department="Engineering",
        seniority="Senior",
        status=ContactStatus.ACTIVE,
        linkedin_url="https://linkedin.example/ada",
        headline="Computing pioneer",
        profile_picture_url="https://example.com/ada.png",
        notes="Important contact",
        contact_profile={"persona": "technical"},
        linkedin_followers=["user-2"],
        organization_id="org-1",
        owner_id="user-1",
        tenant_id="tenant-1",
        created_by="user@example.com",
        updated_by=None,
    )
    contact.created_at = NOW
    contact.updated_at = NOW
    contact.version = 1
    contact.is_deleted = False
    contact.deleted_at = None
    contact.deleted_by = None
    contact.deleted_reason = None
    for key, value in overrides.items():
        setattr(contact, key, value)
    return contact


class FakeContactRepository:
    def __init__(self, db):
        self.db = db
        self.contacts = {"contact-1": make_contact()}

    def create(self, contact):
        contact.id = "contact-new"
        contact.created_at = NOW
        contact.updated_at = NOW
        contact.version = 1
        contact.is_deleted = False
        self.contacts[contact.id] = contact
        return contact

    def get_by_id(self, contact_id, tenant_id):
        contact = self.contacts.get(contact_id)
        return contact if contact and contact.tenant_id == tenant_id and not contact.is_deleted else None

    def list_all(self, tenant_id, skip=0, limit=50, search=None, organization_id=None):
        items = [c for c in self.contacts.values() if c.tenant_id == tenant_id and not c.is_deleted]
        if search:
            needle = search.lower()
            items = [c for c in items if needle in c.first_name.lower() or needle in c.last_name.lower()]
        if organization_id:
            items = [c for c in items if c.organization_id == organization_id]
        return items[skip : skip + limit]

    def count(self, tenant_id, organization_id=None):
        return len(self.list_all(tenant_id, organization_id=organization_id))

    def update(self, contact):
        contact.updated_at = NOW
        contact.version = (contact.version or 0) + 1
        return contact

    def soft_delete(self, contact, deleted_by, reason=None):
        contact.is_deleted = True
        contact.deleted_at = NOW
        contact.deleted_by = deleted_by
        contact.deleted_reason = reason
        contact.version = (contact.version or 0) + 1
        return contact


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
        self.contact = make_contact()

    def query(self, entity):
        if entity is Contact:
            return FakeQuery(self.contact, [self.contact], 1)
        return FakeQuery()


@pytest.fixture()
def repo():
    return FakeContactRepository(FakeDB())


@pytest.fixture()
def client(monkeypatch, repo):
    async def noop_publish(*args, **kwargs):
        return None

    monkeypatch.setattr(contact_routes, "ContactRepository", lambda db: repo)
    monkeypatch.setattr(contact_routes, "publish_contact_created", noop_publish)
    monkeypatch.setattr(contact_routes, "publish_contact_updated", noop_publish)
    monkeypatch.setattr(contact_routes, "publish_contact_deleted", noop_publish)
    main.app.dependency_overrides[contact_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[contact_routes.get_db] = lambda: FakeDB()
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


def test_contact_crud_routes(client):
    created = client.post(
        "/api/v1/contacts",
        json={
            "first_name": "Grace",
            "last_name": "Hopper",
            "email": "grace@example.com",
            "organization_id": "org-1",
        },
    )
    assert created.status_code == 201
    assert created.json()["id"] == "contact-new"

    listed = client.get("/api/v1/contacts", params={"search": "Ada", "organization_id": "org-1"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert client.get("/api/v1/contacts/contact-1").json()["id"] == "contact-1"
    assert client.get("/api/v1/contacts/missing").status_code == 404
    assert client.patch("/api/v1/contacts/contact-1", json={"first_name": "Updated"}).json()["first_name"] == "Updated"
    assert client.patch("/api/v1/contacts/missing", json={"first_name": "Updated"}).status_code == 404
    assert client.delete("/api/v1/contacts/contact-1").status_code == 204
    assert client.delete("/api/v1/contacts/missing").status_code == 404


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
    await publishers.publish_contact_created("contact-1", {"email": "ada@example.com"})
    await publishers.publish_contact_updated("contact-1", {"first_name": "Updated"})
    await publishers.publish_contact_deleted("contact-1")
    assert [event.event_type for event in published] == [
        "contact.created",
        "contact.updated",
        "contact.deleted",
    ]
    assert [event.payload["entity_id"] for event in published] == ["contact-1", "contact-1", "contact-1"]


def test_repository_methods_cover_persistence_paths():
    session = RepositorySession()
    repository = ContactRepository(session)

    assert repository.create(make_contact("contact-new")).id == "contact-new"
    assert repository.get_by_id("contact-1", "tenant-1").id == "contact-1"
    assert repository.list_all("tenant-1", search="Ada", organization_id="org-1")[0].id == "contact-1"
    assert repository.count("tenant-1", organization_id="org-1") == 1
    assert repository.update(session.contact).version == 2
    deleted = repository.soft_delete(session.contact, "user@example.com", reason="duplicate")
    assert deleted.is_deleted is True
    assert deleted.deleted_reason == "duplicate"
    assert session.commits >= 1


def test_database_facade_and_schema_contracts(monkeypatch):
    monkeypatch.setattr(database, "create_db_engine", lambda api_name: f"engine:{api_name}")
    monkeypatch.setattr(database, "create_session_factory", lambda api_name: f"factory:{api_name}")
    database.init("contact-backend")
    assert database.get_engine() == "engine:contact-backend"
    assert database.get_session_factory() == "factory:contact-backend"

    assert contact_schemas.ContactCreate(first_name="Ada", last_name="Lovelace").status == "ACTIVE"
    assert contact_schemas.ContactUpdate(first_name="Updated").first_name == "Updated"
    response = contact_schemas.ContactResponse.model_validate(make_contact())
    assert response.id == "contact-1"
    assert contact_schemas.ContactListResponse(items=[response], total=1, skip=0, limit=50).total == 1


def test_python_package_contract_loads_runtime_components():
    from contact_backend_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (contact_routes,)
    assert contract.load_runtime_repository_classes() == (ContactRepository,)
    assert contract.load_runtime_entity_classes() == (Contact, ContactStatus)
