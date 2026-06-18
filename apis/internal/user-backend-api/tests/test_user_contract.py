from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.infrastructure.persistence.models.role import Permission, Role, RolePermission, UserRole
from app.infrastructure.persistence.models.tenant import Tenant, TenantPlan, TenantStatus
from app.infrastructure.persistence.models.user import User
from app.events import publishers
from app.infrastructure import database
from app.infrastructure.persistence.role_repository import RoleRepository
from app.infrastructure.persistence.tenant_repository import TenantRepository
from app.infrastructure.persistence.user_repository import UserRepository
from app.middleware.auth import get_current_user, settings
from app.presentation.routes import role_routes, tenant_routes, user_routes
from app.presentation.schemas import role_schemas, tenant_schemas, user_schemas


USER = {"user_id": "user-1", "email": "admin@example.com", "tenant_id": "tenant-1"}
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
PASSWORD = "Secret123!"
HASHED_PASSWORD = User.hash_password(PASSWORD)


def make_user(user_id="user-1", **overrides):
    user = User(
        id=user_id,
        email="ada@example.com",
        password_hash=HASHED_PASSWORD,
        first_name="Ada",
        last_name="Lovelace",
        job_title="Architect",
        phone="555-0100",
        bio="Computing pioneer",
        location="Montreal",
        timezone="America/Montreal",
        role="member",
        is_super_admin=False,
        trust_score=0.7,
        active_organization_id="org-1",
        tenant_id="tenant-1",
        created_by="admin@example.com",
        updated_by=None,
    )
    user.created_at = NOW
    user.updated_at = NOW
    user.version = 1
    user.is_deleted = False
    user.deleted_at = None
    user.deleted_by = None
    for key, value in overrides.items():
        setattr(user, key, value)
    return user


def make_tenant(tenant_id="tenant-1", **overrides):
    tenant = Tenant(
        id=tenant_id,
        name="Tenant",
        slug="tenant",
        status=TenantStatus.TRIAL,
        plan=TenantPlan.STARTER,
        owner_email="owner@example.com",
        owner_name="Owner",
        max_users=5,
        subscription_start=None,
        subscription_end=None,
        settings={"locale": "fr-CA"},
        notes="Tenant notes",
        created_by="system",
        updated_by=None,
    )
    tenant.created_at = NOW
    tenant.updated_at = NOW
    tenant.version = 1
    tenant.is_deleted = False
    tenant.deleted_at = None
    tenant.deleted_by = None
    for key, value in overrides.items():
        setattr(tenant, key, value)
    return tenant


def make_permission(permission_id="perm-1", **overrides):
    permission = Permission(
        id=permission_id,
        resource="users",
        action="read",
        description="Read users",
    )
    for key, value in overrides.items():
        setattr(permission, key, value)
    return permission


def make_role(role_id="role-1", **overrides):
    role = Role(
        id=role_id,
        name="member",
        description="Member role",
        is_system=False,
        tenant_id="tenant-1",
        created_by="system",
        updated_by=None,
    )
    role.created_at = NOW
    role.updated_at = NOW
    role.version = 1
    role.permissions = [make_permission()]
    for key, value in overrides.items():
        setattr(role, key, value)
    return role


def make_user_role(user_role_id="user-role-1", **overrides):
    user_role = UserRole(id=user_role_id, user_id="user-1", role_id="role-1")
    user_role.role = make_role()
    for key, value in overrides.items():
        setattr(user_role, key, value)
    return user_role


class FakeUserRepository:
    def __init__(self, db):
        self.db = db
        self.users = {"user-1": make_user(), "user-2": make_user("user-2", email="member@example.com")}

    def create(self, user):
        user.id = "user-new"
        user.created_at = NOW
        user.updated_at = NOW
        user.version = 1
        user.is_deleted = False
        user.trust_score = user.trust_score if user.trust_score is not None else 0.1
        user.timezone = user.timezone or "America/Montreal"
        self.users[user.id] = user
        return user

    def get_by_id(self, user_id):
        user = self.users.get(user_id)
        return user if user and not user.is_deleted else None

    def get_by_email(self, email):
        for user in self.users.values():
            if user.email.lower() == email.lower() and not user.is_deleted:
                return user
        return None

    def update(self, user):
        user.updated_at = NOW
        user.version = (user.version or 0) + 1
        return user

    def list_by_tenant(self, tenant_id, skip=0, limit=50):
        users = [u for u in self.users.values() if u.tenant_id == tenant_id and not u.is_deleted]
        return users[skip : skip + limit], len(users)

    def soft_delete(self, user_id):
        user = self.get_by_id(user_id)
        if not user:
            return False
        user.is_deleted = True
        user.version = (user.version or 0) + 1
        return True


class FakeTenantRepository:
    def __init__(self, db):
        self.db = db
        self.tenants = {"tenant-1": make_tenant()}

    def create(self, **kwargs):
        tenant = make_tenant("tenant-new", **kwargs)
        self.tenants[tenant.id] = tenant
        return tenant

    def get_by_id(self, tenant_id):
        tenant = self.tenants.get(tenant_id)
        return tenant if tenant and not tenant.is_deleted else None

    def get_by_slug(self, slug):
        for tenant in self.tenants.values():
            if tenant.slug == slug and not tenant.is_deleted:
                return tenant
        return None

    def get_all(self, search=None, status=None, skip=0, limit=50):
        tenants = [t for t in self.tenants.values() if not t.is_deleted]
        if search:
            tenants = [t for t in tenants if search.lower() in t.name.lower()]
        if status:
            tenants = [t for t in tenants if t.status == status or getattr(t.status, "value", t.status) == status]
        return tenants[skip : skip + limit], len(tenants)

    def update(self, tenant, **kwargs):
        for key, value in kwargs.items():
            if value is not None:
                setattr(tenant, key, value)
        tenant.updated_at = NOW
        return tenant

    def soft_delete(self, tenant):
        tenant.is_deleted = True


class FakeRoleRepository:
    def __init__(self, db):
        self.db = db
        self.permissions = {"perm-1": make_permission()}
        self.roles = {"role-1": make_role(), "role-system": make_role("role-system", is_system=True)}

    def list_permissions(self):
        return list(self.permissions.values())

    def create_role(self, role):
        role.id = "role-new"
        role.permissions = []
        self.roles[role.id] = role
        return role

    def get_role_by_id(self, role_id, tenant_id):
        role = self.roles.get(role_id)
        return role if role and role.tenant_id == tenant_id else None

    def get_role_by_name(self, name, tenant_id):
        for role in self.roles.values():
            if role.name == name and role.tenant_id == tenant_id:
                return role
        return None

    def list_roles(self, tenant_id):
        return [role for role in self.roles.values() if role.tenant_id == tenant_id]

    def update_role(self, role):
        return role

    def delete_role(self, role):
        if role.is_system:
            return False
        self.roles.pop(role.id, None)
        return True

    def set_role_permissions(self, role_id, permission_ids):
        role = self.roles[role_id]
        role.permissions = [self.permissions[pid] for pid in permission_ids if pid in self.permissions]

    def get_user_roles(self, user_id):
        return [self.roles["role-1"]] if user_id == "user-1" else []

    def get_user_permissions(self, user_id):
        return ["users:read"] if user_id == "user-1" else []

    def assign_role_to_user(self, user_id, role_id):
        self.assigned = (user_id, role_id)

    def remove_role_from_user(self, user_id, role_id):
        self.removed = (user_id, role_id)


class FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.refreshed = []
        self.deleted = []
        self.flushed = 0

    def add(self, entity):
        self.added.append(entity)

    def commit(self):
        self.commits += 1

    def refresh(self, entity):
        self.refreshed.append(entity)

    def delete(self, entity):
        self.deleted.append(entity)

    def flush(self):
        self.flushed += 1

    def query(self, entity):
        return FakeQuery()


class FakeQuery:
    def __init__(self, result=None, results=None, count_value=1):
        self.result = result
        self.results = list(results or [])
        self.count_value = count_value
        self.deleted = False

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

    def delete(self):
        self.deleted = True


class RepositorySession(FakeDB):
    def __init__(self):
        super().__init__()
        self.user = make_user()
        self.tenant = make_tenant()
        self.permission = make_permission()
        self.role = make_role()
        self.role_permission = RolePermission(id="role-perm-1", role_id="role-1", permission_id="perm-1")
        self.user_role = make_user_role()

    def query(self, entity):
        if entity is User:
            return FakeQuery(self.user, [self.user], 1)
        if entity is Tenant:
            return FakeQuery(self.tenant, [self.tenant], 1)
        if entity is Permission:
            return FakeQuery(self.permission, [self.permission], 1)
        if entity is Role:
            return FakeQuery(self.role, [self.role], 1)
        if entity is RolePermission:
            return FakeQuery(self.role_permission, [self.role_permission], 1)
        if entity is UserRole:
            return FakeQuery(self.user_role, [self.user_role], 1)
        return FakeQuery()


@pytest.fixture()
def repos():
    db = FakeDB()
    return FakeUserRepository(db), FakeTenantRepository(db), FakeRoleRepository(db)


@pytest.fixture()
def client(monkeypatch, repos):
    user_repo, tenant_repo, role_repo = repos

    async def noop_publish(*args, **kwargs):
        return None

    monkeypatch.setattr(user_routes, "UserRepository", lambda db: user_repo)
    monkeypatch.setattr(user_routes, "RoleRepository", lambda db: role_repo)
    monkeypatch.setattr(user_routes.User, "hash_password", staticmethod(lambda password: HASHED_PASSWORD))
    monkeypatch.setattr(tenant_routes, "TenantRepository", lambda db: tenant_repo)
    monkeypatch.setattr(role_routes, "RoleRepository", lambda db: role_repo)
    monkeypatch.setattr(user_routes, "publish_user_created", noop_publish)
    monkeypatch.setattr(user_routes, "publish_user_updated", noop_publish)
    monkeypatch.setattr(user_routes, "publish_user_deleted", noop_publish)
    main.app.dependency_overrides[user_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[user_routes.get_db] = lambda: FakeDB()
    main.app.dependency_overrides[tenant_routes.get_db] = lambda: FakeDB()
    main.app.dependency_overrides[role_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[role_routes.get_db] = lambda: FakeDB()
    test_client = TestClient(main.app)
    yield test_client
    test_client.close()
    main.app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers():
    token = jwt.encode(
        {"sub": "user-1", "email": "admin@example.com", "tenant_id": "tenant-1"},
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


def test_user_routes(client):
    listed = client.get("/api/v1/users")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert client.get("/api/v1/users/user-1").json()["id"] == "user-1"
    assert client.get("/api/v1/users/missing").status_code == 404
    assert client.get("/api/v1/users/by-email/ada@example.com").json()["email"] == "ada@example.com"
    assert client.get("/api/v1/users/by-email/missing@example.com").status_code == 404

    created = client.post(
        "/api/v1/users",
        json={
            "email": "new@example.com",
            "password": PASSWORD,
            "first_name": "New",
            "last_name": "User",
            "tenant_id": "tenant-1",
            "role": "member",
        },
    )
    assert created.status_code == 201
    assert created.json()["id"] == "user-new"
    assert client.post(
        "/api/v1/users",
        json={
            "email": "ada@example.com",
            "password": PASSWORD,
            "first_name": "Ada",
            "last_name": "Lovelace",
        },
    ).status_code == 409

    assert client.patch("/api/v1/users/user-1", json={"first_name": "Updated"}).json()["first_name"] == "Updated"
    assert client.patch("/api/v1/users/missing", json={"first_name": "Updated"}).status_code == 404
    assert client.delete("/api/v1/users/user-2").status_code == 204
    assert client.delete("/api/v1/users/missing").status_code == 404
    assert client.post("/api/v1/users/verify-password", json={"email": "ada@example.com", "password": PASSWORD}).json() == {
        "valid": True
    }
    assert client.post("/api/v1/users/verify-password", json={"email": "missing@example.com", "password": PASSWORD}).json() == {
        "valid": False
    }


def test_tenant_routes(client):
    listed = client.get("/api/v1/tenants", params={"search": "Tenant", "status": "TRIAL"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert client.get("/api/v1/tenants/tenant-1").json()["id"] == "tenant-1"
    assert client.get("/api/v1/tenants/missing").status_code == 404
    assert client.get("/api/v1/tenants/by-slug/tenant").json()["slug"] == "tenant"
    assert client.get("/api/v1/tenants/by-slug/missing").status_code == 404

    created = client.post(
        "/api/v1/tenants",
        json={"name": "New tenant", "slug": "new-tenant", "owner_email": "owner@example.com", "owner_name": "Owner"},
    )
    assert created.status_code == 201
    assert created.json()["id"] == "tenant-new"
    assert client.post(
        "/api/v1/tenants",
        json={"name": "Tenant", "slug": "tenant", "owner_email": "owner@example.com", "owner_name": "Owner"},
    ).status_code == 409
    assert client.patch("/api/v1/tenants/tenant-1", json={"name": "Updated"}).json()["name"] == "Updated"
    assert client.patch("/api/v1/tenants/missing", json={"name": "Updated"}).status_code == 404
    assert client.delete("/api/v1/tenants/tenant-1").status_code == 204
    assert client.delete("/api/v1/tenants/missing").status_code == 404


def test_role_routes(client):
    assert client.get("/api/v1/roles/permissions").json()[0]["id"] == "perm-1"
    roles = client.get("/api/v1/roles")
    assert roles.status_code == 200
    assert roles.json()["total"] >= 1

    created = client.post("/api/v1/roles", json={"name": "custom", "description": "Custom role"})
    assert created.status_code == 201
    assert created.json()["id"] == "role-new"
    assert client.post("/api/v1/roles", json={"name": "member"}).status_code == 409
    assert client.get("/api/v1/roles/role-1").json()["id"] == "role-1"
    assert client.get("/api/v1/roles/missing").status_code == 404
    assert client.patch("/api/v1/roles/role-1", json={"name": "renamed"}).json()["name"] == "renamed"
    assert client.patch("/api/v1/roles/missing", json={"name": "renamed"}).status_code == 404
    assert client.delete("/api/v1/roles/role-new").status_code == 204
    assert client.delete("/api/v1/roles/role-system").status_code == 403
    assert client.delete("/api/v1/roles/missing").status_code == 404

    assert client.put("/api/v1/roles/role-1/permissions", json={"permission_ids": ["perm-1"]}).json()["permissions"][0]["id"] == "perm-1"
    assert client.put("/api/v1/roles/missing/permissions", json={"permission_ids": ["perm-1"]}).status_code == 404
    assert client.get("/api/v1/roles/users/user-1/roles").json()["roles"][0]["id"] == "role-1"
    assert client.get("/api/v1/roles/users/user-1/permissions").json()["permissions"] == ["users:read"]
    assert client.post("/api/v1/roles/users/user-1/roles", json={"role_id": "role-1"}).json()["message"] == "Role assigned"
    assert client.delete("/api/v1/roles/users/user-1/roles/role-1").status_code == 204


def test_auth_dependency_accepts_and_rejects_tokens(auth_headers):
    credentials = type("Credentials", (), {"credentials": auth_headers["Authorization"].split(" ", 1)[1]})()
    assert get_current_user(credentials)["tenant_id"] == "tenant-1"

    invalid = type("Credentials", (), {"credentials": "not-a-token"})()
    with pytest.raises(Exception) as invalid_token:
        get_current_user(invalid)
    assert getattr(invalid_token.value, "status_code", None) == 401

    no_sub = jwt.encode({"email": "admin@example.com"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(Exception) as missing_sub:
        get_current_user(type("Credentials", (), {"credentials": no_sub})())
    assert getattr(missing_sub.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_publishers_emit_domain_events(monkeypatch):
    published = []

    async def fake_publish(event):
        published.append(event)

    monkeypatch.setattr(publishers.event_bus, "publish", fake_publish)
    await publishers.publish_user_created("user-1", {"email": "ada@example.com"})
    await publishers.publish_user_updated("user-1", {"email": "updated@example.com"})
    await publishers.publish_user_deleted("user-1")
    assert [event.event_type for event in published] == ["user.created", "user.updated", "user.deleted"]
    assert [event.payload["entity_id"] for event in published] == ["user-1", "user-1", "user-1"]


def test_repository_methods_cover_persistence_paths():
    session = RepositorySession()
    user_repository = UserRepository(session)
    tenant_repository = TenantRepository(session)
    role_repository = RoleRepository(session)

    assert user_repository.create(make_user("user-new")).id == "user-new"
    assert user_repository.get_by_id("user-1").id == "user-1"
    assert user_repository.get_by_email("ada@example.com").id == "user-1"
    assert user_repository.update(session.user).version == 2
    assert user_repository.list_by_tenant("tenant-1")[1] == 1
    assert user_repository.soft_delete("user-1") is True

    assert tenant_repository.create(name="New", slug="new", owner_email="owner@example.com", owner_name="Owner").slug == "new"
    assert tenant_repository.get_by_id("tenant-1").id == "tenant-1"
    assert tenant_repository.get_by_slug("tenant").slug == "tenant"
    assert tenant_repository.get_all(search="Tenant", status="TRIAL")[1] == 1
    assert tenant_repository.update(session.tenant, name="Updated").name == "Updated"
    tenant_repository.soft_delete(session.tenant)
    assert session.tenant.is_deleted is True

    assert role_repository.get_or_create_permission("users", "read").id == "perm-1"
    assert role_repository.list_permissions()[0].id == "perm-1"
    assert role_repository.create_role(make_role("role-new")).id == "role-new"
    assert role_repository.get_role_by_id("role-1", "tenant-1").id == "role-1"
    assert role_repository.get_role_by_name("member", "tenant-1").id == "role-1"
    assert role_repository.list_roles("tenant-1")[0].id == "role-1"
    assert role_repository.update_role(session.role).id == "role-1"
    assert role_repository.delete_role(session.role) is True
    role_repository.assign_permission_to_role("role-1", "perm-1")
    role_repository.remove_permission_from_role("role-1", "perm-1")
    role_repository.set_role_permissions("role-1", ["perm-1"])
    role_repository.assign_role_to_user("user-1", "role-1")
    role_repository.remove_role_from_user("user-1", "role-1")
    assert role_repository.get_user_roles("user-1")[0].id == "role-1"
    assert role_repository.get_user_permissions("user-1") == ["users:read"]
    assert session.commits >= 1


def test_database_facade_and_schema_contracts(monkeypatch):
    monkeypatch.setattr(database, "create_db_engine", lambda api_name: f"engine:{api_name}")
    monkeypatch.setattr(database, "create_session_factory", lambda api_name: f"factory:{api_name}")
    database.init("user-backend")
    assert database.get_engine() == "engine:user-backend"
    assert database.get_session_factory() == "factory:user-backend"

    assert user_schemas.UserCreateRequest(
        email="new@example.com",
        password=PASSWORD,
        first_name="New",
        last_name="User",
    ).role == "member"
    assert user_schemas.UserUpdateRequest(first_name="Updated").first_name == "Updated"
    assert user_schemas.UserResponse.model_validate(make_user()).id == "user-1"

    assert tenant_schemas.TenantCreateRequest(
        name="Tenant",
        slug="tenant-2",
        owner_email="owner@example.com",
        owner_name="Owner",
    ).plan == "STARTER"
    assert tenant_schemas.TenantUpdateRequest(name="Updated").name == "Updated"
    assert tenant_schemas.TenantResponse.model_validate(make_tenant()).id == "tenant-1"

    assert role_schemas.PermissionResponse.model_validate(make_permission()).id == "perm-1"
    assert role_schemas.RoleCreateRequest(name="custom").name == "custom"
    assert role_schemas.RoleUpdateRequest(name="renamed").name == "renamed"
    assert role_schemas.RoleResponse.model_validate(make_role()).id == "role-1"
    assert role_schemas.AssignPermissionsRequest(permission_ids=["perm-1"]).permission_ids == ["perm-1"]
    assert role_schemas.AssignRoleRequest(role_id="role-1").role_id == "role-1"
    assert role_schemas.UserRoleResponse(user_id="user-1", roles=[role_schemas.RoleResponse.model_validate(make_role())]).user_id == "user-1"


def test_seed_helpers_cover_admin_and_permission_matching(monkeypatch):
    from app.infrastructure import seed, seed_roles

    created = []

    class FakeSeedRepository:
        existing = make_user("admin-1", email="admin@example.com")

        def __init__(self, db):
            self.db = db

        def get_by_email(self, email):
            return self.existing

        def create(self, user):
            user.id = "admin-new"
            user.created_at = NOW
            user.updated_at = NOW
            user.version = 1
            user.is_deleted = False
            user.trust_score = 0.1
            created.append(user)
            return user

    monkeypatch.setattr(seed, "UserRepository", FakeSeedRepository)
    monkeypatch.setattr(seed, "settings", SimpleNamespace(
        admin_email="admin@example.com",
        admin_password=PASSWORD,
        admin_first_name="Admin",
        admin_last_name="User",
    ))
    monkeypatch.setattr(seed.User, "hash_password", staticmethod(lambda password: HASHED_PASSWORD))

    seed.seed_admin_user(FakeDB())
    assert created == []

    FakeSeedRepository.existing = None
    seed.run_seed(FakeDB())
    assert created[0].email == "admin@example.com"
    assert created[0].role == "admin"

    assert seed_roles._match_permission("user:read", ["user:*"]) is True
    assert seed_roles._match_permission("user:write", ["user:read"]) is False


def test_python_package_contract_loads_runtime_components():
    from user_backend_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (user_routes, tenant_routes, role_routes)
    assert contract.load_runtime_repository_classes() == (UserRepository, TenantRepository, RoleRepository)
    assert contract.load_runtime_entity_classes() == (
        User,
        Tenant,
        TenantStatus,
        TenantPlan,
        Permission,
        Role,
        RolePermission,
        UserRole,
    )
