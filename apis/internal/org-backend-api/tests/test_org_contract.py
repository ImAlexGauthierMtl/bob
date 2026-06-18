from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.domain.entities.department import Department, UserDepartment
from app.domain.entities.organization import Organization, OrganizationStatus, OrganizationType
from app.events import publishers
from app.infrastructure import database
from app.infrastructure.persistence.department_repository import DepartmentRepository
from app.infrastructure.persistence.organization_repository import OrganizationRepository
from app.middleware.auth import get_current_user, settings
from app.presentation.routes import department_routes, organization_routes
from app.presentation.schemas import department_schemas, organization_schemas


USER = {"user_id": "user-1", "email": "user@example.com", "tenant_id": "tenant-1"}
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_organization(org_id="org-1", **overrides):
    org = Organization(
        id=org_id,
        name="Croo",
        industry="Technology",
        website="https://croo.example",
        phone="555-0100",
        email="hello@croo.example",
        address_street="1 Main",
        address_city="Montreal",
        address_state="QC",
        address_country="CA",
        address_postal_code="H2X 1A1",
        status=OrganizationStatus.PROSPECT,
        org_type=OrganizationType.STARTUP,
        employee_count=42,
        annual_revenue=1000000.0,
        description="Digital experience",
        ai_enriched="N",
        linkedin_url="https://linkedin.example/croo",
        logo_url="https://example.com/logo.png",
        organization_profile={"segment": "b2b"},
        linkedin_followers=100,
        linkedin_employees=25,
        linkedin_specialties=["ai"],
        owner_id="user-1",
        tenant_id="tenant-1",
        created_by="user@example.com",
        updated_by=None,
    )
    org.created_at = NOW
    org.updated_at = NOW
    org.version = 1
    org.is_deleted = False
    org.deleted_at = None
    org.deleted_by = None
    org.deleted_reason = None
    for key, value in overrides.items():
        setattr(org, key, value)
    return org


def make_department(dept_id="dept-1", **overrides):
    dept = Department(
        id=dept_id,
        name="Engineering",
        description="Builds the product",
        manager_user_id="user-1",
        tenant_id="tenant-1",
        created_by="user@example.com",
        updated_by=None,
    )
    dept.created_at = NOW
    dept.updated_at = NOW
    dept.version = 1
    dept.is_deleted = False
    dept.deleted_at = None
    dept.deleted_by = None
    for key, value in overrides.items():
        setattr(dept, key, value)
    return dept


class FakeOrganizationRepository:
    def __init__(self, db):
        self.db = db
        self.organizations = {"org-1": make_organization()}

    def create(self, org):
        org.id = "org-new"
        org.created_at = NOW
        org.updated_at = NOW
        org.version = 1
        org.is_deleted = False
        self.organizations[org.id] = org
        return org

    def get_by_id(self, org_id, tenant_id):
        org = self.organizations.get(org_id)
        return org if org and org.tenant_id == tenant_id and not org.is_deleted else None

    def list_all(self, tenant_id, skip=0, limit=50, search=None):
        items = [o for o in self.organizations.values() if o.tenant_id == tenant_id and not o.is_deleted]
        if search:
            items = [o for o in items if search.lower() in o.name.lower()]
        return items[skip : skip + limit]

    def count(self, tenant_id):
        return len(self.list_all(tenant_id))

    def update(self, org):
        org.updated_at = NOW
        org.version = (org.version or 0) + 1
        return org

    def soft_delete(self, org, deleted_by, reason=None):
        org.is_deleted = True
        org.deleted_at = NOW
        org.deleted_by = deleted_by
        org.deleted_reason = reason
        org.version = (org.version or 0) + 1
        return org


class FakeDepartmentRepository:
    def __init__(self, db):
        self.db = db
        self.departments = {"dept-1": make_department()}

    def create(self, dept):
        dept.id = "dept-new"
        dept.created_at = NOW
        dept.updated_at = NOW
        dept.version = 1
        dept.is_deleted = False
        self.departments[dept.id] = dept
        return dept

    def get_by_id(self, dept_id, tenant_id):
        dept = self.departments.get(dept_id)
        return dept if dept and dept.tenant_id == tenant_id and not dept.is_deleted else None

    def list_all(self, tenant_id):
        return [d for d in self.departments.values() if d.tenant_id == tenant_id and not d.is_deleted]

    def update(self, dept):
        dept.updated_at = NOW
        dept.version = (dept.version or 0) + 1
        return dept

    def soft_delete(self, dept, deleted_by):
        dept.is_deleted = True
        dept.deleted_at = NOW
        dept.deleted_by = deleted_by
        dept.version = (dept.version or 0) + 1
        return dept


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
        self.organization = make_organization()
        self.department = make_department()

    def query(self, entity):
        if entity is Organization:
            return FakeQuery(self.organization, [self.organization], 1)
        if entity is Department:
            return FakeQuery(self.department, [self.department], 1)
        return FakeQuery()


@pytest.fixture()
def repos():
    db = FakeDB()
    return FakeOrganizationRepository(db), FakeDepartmentRepository(db)


@pytest.fixture()
def client(monkeypatch, repos):
    org_repo, dept_repo = repos

    async def noop_publish(*args, **kwargs):
        return None

    monkeypatch.setattr(organization_routes, "OrganizationRepository", lambda db: org_repo)
    monkeypatch.setattr(department_routes, "DepartmentRepository", lambda db: dept_repo)
    monkeypatch.setattr(organization_routes, "publish_org_created", noop_publish)
    monkeypatch.setattr(organization_routes, "publish_org_updated", noop_publish)
    monkeypatch.setattr(organization_routes, "publish_org_deleted", noop_publish)
    main.app.dependency_overrides[organization_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[organization_routes.get_db] = lambda: FakeDB()
    main.app.dependency_overrides[department_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[department_routes.get_db] = lambda: FakeDB()
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


def test_organization_crud_routes(client):
    created = client.post(
        "/api/v1/organizations",
        json={"name": "New Org", "industry": "Services", "status": "CUSTOMER"},
    )
    assert created.status_code == 201
    assert created.json()["id"] == "org-new"

    listed = client.get("/api/v1/organizations", params={"search": "Croo"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert client.get("/api/v1/organizations/org-1").json()["id"] == "org-1"
    assert client.get("/api/v1/organizations/missing").status_code == 404
    assert client.patch("/api/v1/organizations/org-1", json={"name": "Updated"}).json()["name"] == "Updated"
    assert client.patch("/api/v1/organizations/missing", json={"name": "Updated"}).status_code == 404
    assert client.delete("/api/v1/organizations/org-1").status_code == 204
    assert client.delete("/api/v1/organizations/missing").status_code == 404


def test_department_crud_routes(client):
    created = client.post("/api/v1/departments", json={"name": "Support", "manager_user_id": "user-2"})
    assert created.status_code == 201
    assert created.json()["id"] == "dept-new"

    listed = client.get("/api/v1/departments")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == "dept-1"
    assert client.get("/api/v1/departments/dept-1").json()["id"] == "dept-1"
    assert client.get("/api/v1/departments/missing").status_code == 404
    assert client.patch("/api/v1/departments/dept-1", json={"name": "Updated"}).json()["name"] == "Updated"
    assert client.patch("/api/v1/departments/missing", json={"name": "Updated"}).status_code == 404
    assert client.delete("/api/v1/departments/dept-1").status_code == 204
    assert client.delete("/api/v1/departments/missing").status_code == 404


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
    await publishers.publish_org_created("org-1", {"name": "Croo"})
    await publishers.publish_org_updated("org-1", {"name": "Updated"})
    await publishers.publish_org_deleted("org-1")
    assert [event.event_type for event in published] == [
        "organization.created",
        "organization.updated",
        "organization.deleted",
    ]
    assert [event.payload["entity_id"] for event in published] == ["org-1", "org-1", "org-1"]


def test_repository_methods_cover_persistence_paths():
    session = RepositorySession()
    org_repository = OrganizationRepository(session)
    dept_repository = DepartmentRepository(session)

    assert org_repository.create(make_organization("org-new")).id == "org-new"
    assert org_repository.get_by_id("org-1", "tenant-1").id == "org-1"
    assert org_repository.list_all("tenant-1", search="Croo")[0].id == "org-1"
    assert org_repository.count("tenant-1") == 1
    assert org_repository.update(session.organization).version == 2
    org_deleted = org_repository.soft_delete(session.organization, "user@example.com", reason="duplicate")
    assert org_deleted.is_deleted is True
    assert org_deleted.deleted_reason == "duplicate"

    assert dept_repository.create(make_department("dept-new")).id == "dept-new"
    assert dept_repository.get_by_id("dept-1", "tenant-1").id == "dept-1"
    assert dept_repository.list_all("tenant-1")[0].id == "dept-1"
    assert dept_repository.update(session.department).version == 2
    assert dept_repository.soft_delete(session.department, "user@example.com").is_deleted is True
    assert session.commits >= 1


def test_database_facade_and_schema_contracts(monkeypatch):
    monkeypatch.setattr(database, "create_db_engine", lambda api_name: f"engine:{api_name}")
    monkeypatch.setattr(database, "create_session_factory", lambda api_name: f"factory:{api_name}")
    database.init("org-backend")
    assert database.get_engine() == "engine:org-backend"
    assert database.get_session_factory() == "factory:org-backend"

    assert organization_schemas.OrganizationCreate(name="Croo").status == "PROSPECT"
    assert organization_schemas.OrganizationUpdate(name="Updated").name == "Updated"
    org_response = organization_schemas.OrganizationResponse.model_validate(make_organization())
    assert org_response.id == "org-1"
    assert organization_schemas.OrganizationListResponse(items=[org_response], total=1, skip=0, limit=50).total == 1

    assert department_schemas.DepartmentCreate(name="Engineering").name == "Engineering"
    assert department_schemas.DepartmentUpdate(name="Updated").name == "Updated"
    assert department_schemas.DepartmentResponse.model_validate(make_department()).id == "dept-1"


def test_python_package_contract_loads_runtime_components():
    from org_backend_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (organization_routes, department_routes)
    assert contract.load_runtime_repository_classes() == (OrganizationRepository, DepartmentRepository)
    assert contract.load_runtime_entity_classes() == (
        Organization,
        OrganizationStatus,
        OrganizationType,
        Department,
        UserDepartment,
    )
