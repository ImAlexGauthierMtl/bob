from datetime import datetime, timezone

import pytest
import httpx
from fastapi.testclient import TestClient

import main
from app.infrastructure.clients.user_client import RoleClient, TenantClient, UserClient
from app.presentation.routes import auth_routes, bob_cloud_auth_routes, role_routes, tenant_routes, user_routes
from shared.services import BobCloudModeError, BobCloudResponseError


def user_payload(user_id="user-1", email="user@example.com", **overrides):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    payload = {
        "id": user_id,
        "email": email,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "role": "admin",
        "tenant_id": "tenant-1",
        "active_organization_id": "org-1",
        "is_super_admin": True,
        "created_at": now,
        "updated_at": now,
    }
    payload.update(overrides)
    return payload


def role_payload(role_id="role-admin", name="admin", **overrides):
    payload = {
        "id": role_id,
        "name": name,
        "description": "Administrator",
        "is_system": False,
        "permissions": [
            {"id": "perm-users", "resource": "users", "action": "manage", "description": "Manage users"}
        ],
    }
    payload.update(overrides)
    return payload


def tenant_payload(tenant_id="tenant-1", **overrides):
    payload = {
        "id": tenant_id,
        "name": "Croo",
        "slug": "croo",
        "status": "ACTIVE",
        "plan": "TEAM",
        "owner_email": "owner@example.com",
        "owner_name": "Owner",
        "max_users": 25,
    }
    payload.update(overrides)
    return payload


class FakeUserClient:
    async def get_by_id(self, user_id, forward_headers=None):
        if user_id == "missing":
            return None
        return user_payload(user_id=user_id)

    async def get_by_email(self, email, forward_headers=None):
        if email == "missing@example.com":
            return None
        if email == "new@example.com":
            return None
        return user_payload(email=email)

    async def create(self, data, forward_headers=None):
        payload = data.copy()
        email = payload.pop("email")
        return user_payload(user_id="created-user", email=email, **payload)

    async def update(self, user_id, data, forward_headers=None):
        return user_payload(user_id=user_id, **data)

    async def delete(self, user_id, forward_headers=None):
        return user_id != "missing"

    async def list_users(self, skip=0, limit=50, forward_headers=None):
        return {"items": [user_payload()], "total": 1, "skip": skip, "limit": limit}

    async def get_user_roles(self, user_id, forward_headers=None):
        return [role_payload()]

    async def get_user_permissions(self, user_id, forward_headers=None):
        return ["users:manage"]


class FakeTenantClient:
    async def get_by_id(self, tenant_id, forward_headers=None):
        if tenant_id == "missing":
            return None
        return tenant_payload(tenant_id)

    async def get_by_slug(self, slug, forward_headers=None):
        if slug == "missing":
            return None
        return tenant_payload(slug=slug)

    async def create(self, data, forward_headers=None):
        return tenant_payload("tenant-new", **data)

    async def update(self, tenant_id, data, forward_headers=None):
        return tenant_payload(tenant_id, **data)

    async def delete(self, tenant_id, forward_headers=None):
        return tenant_id != "missing"

    async def list_tenants(self, search=None, status=None, skip=0, limit=50, forward_headers=None):
        return {"items": [tenant_payload()], "total": 1}


class FakeRoleClient:
    async def list_roles(self, forward_headers=None):
        return {"items": [role_payload()], "total": 1}

    async def create_role(self, data, forward_headers=None):
        return role_payload("role-new", data["name"], description=data.get("description"))

    async def get_role(self, role_id, forward_headers=None):
        if role_id == "missing":
            return None
        return role_payload(role_id)

    async def update_role(self, role_id, data, forward_headers=None):
        return role_payload(role_id, data.get("name", "admin"), description=data.get("description"))

    async def delete_role(self, role_id, forward_headers=None):
        return role_id != "missing"

    async def set_permissions(self, role_id, permission_ids, forward_headers=None):
        return role_payload(role_id, permissions=[{"id": permission_ids[0], "resource": "users", "action": "read"}])

    async def list_permissions(self, forward_headers=None):
        return [{"id": "perm-users", "resource": "users", "action": "read", "description": "Read users"}]

    async def assign_role(self, user_id, role_id, forward_headers=None):
        return None

    async def remove_role(self, user_id, role_id, forward_headers=None):
        return None


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload or {}
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class FakeServiceClient:
    def __init__(self):
        self.calls = []

    async def get(self, path, params=None, forward_headers=None):
        self.calls.append(("get", path, params, forward_headers))
        if path.endswith("/missing") or "/by-email/missing" in path:
            return FakeResponse(status_code=404)
        if path == "/api/v1/roles/permissions":
            return FakeResponse([{"id": "perm-users", "resource": "users", "action": "read"}])
        if path.endswith("/roles") and "/users/" in path:
            return FakeResponse({"roles": [role_payload()]})
        if path.endswith("/permissions"):
            return FakeResponse({"permissions": ["users:manage"]})
        if path.startswith("/api/v1/tenants"):
            return FakeResponse(tenant_payload())
        if path.startswith("/api/v1/roles"):
            return FakeResponse(role_payload())
        if path == "/api/v1/users":
            return FakeResponse({"items": [user_payload()], "total": 1, "skip": 0, "limit": 50})
        return FakeResponse(user_payload())

    async def post(self, path, json=None, forward_headers=None):
        self.calls.append(("post", path, json, forward_headers))
        if path == "/api/v1/users/verify-password":
            return FakeResponse({"valid": json["password"] == "correct-password"})
        if path.startswith("/api/v1/tenants"):
            return FakeResponse(tenant_payload("tenant-new", **(json or {})), status_code=201)
        if path.startswith("/api/v1/roles"):
            return FakeResponse(role_payload("role-new", (json or {}).get("name", "admin")), status_code=201)
        return FakeResponse(user_payload(user_id="created-user", **(json or {})), status_code=201)

    async def patch(self, path, json=None, forward_headers=None):
        self.calls.append(("patch", path, json, forward_headers))
        if path.startswith("/api/v1/tenants"):
            return FakeResponse(tenant_payload(**(json or {})))
        if path.startswith("/api/v1/roles"):
            return FakeResponse(role_payload(name=(json or {}).get("name", "admin")))
        return FakeResponse(user_payload(**(json or {})))

    async def put(self, path, json=None, forward_headers=None):
        self.calls.append(("put", path, json, forward_headers))
        return FakeResponse(role_payload())

    async def delete(self, path, forward_headers=None):
        self.calls.append(("delete", path, None, forward_headers))
        return FakeResponse(status_code=404 if path.endswith("/missing") else 204)


class FakeBobCloudClient:
    def __init__(self):
        self.calls = []

    async def get_session_response(self, forward_headers=None):
        self.calls.append(("session", dict(forward_headers or {})))
        return httpx.Response(
            200,
            headers={"Set-Cookie": "bob_cloud_session=abc; HttpOnly; Path=/"},
            json={
                "authenticated": True,
                "user": {"id": "user-alex-local"},
                "tenant": {"id": "tenant-croo-local"},
                "source": "bob-cloud-stub",
            },
        )

    async def refresh_session_response(self, forward_headers=None):
        self.calls.append(("refresh", dict(forward_headers or {})))
        return httpx.Response(
            200,
            headers={"Set-Cookie": "bob_cloud_session=refreshed; HttpOnly; Path=/"},
            json={"authenticated": True, "source": "bob-cloud-stub"},
        )

    async def logout_response(self, forward_headers=None):
        self.calls.append(("logout", dict(forward_headers or {})))
        return httpx.Response(
            200,
            headers={"Set-Cookie": "bob_cloud_session=; Max-Age=0; Path=/"},
            json={"authenticated": False, "source": "bob-cloud-stub"},
        )


@pytest.fixture()
def fake_clients(monkeypatch):
    async def skip_admin_seed():
        return None

    fake_user = FakeUserClient()
    fake_tenant = FakeTenantClient()
    fake_role = FakeRoleClient()

    monkeypatch.setattr(main, "seed_admin_user", skip_admin_seed)
    monkeypatch.setattr(auth_routes, "user_client", fake_user)
    monkeypatch.setattr(user_routes, "user_client", fake_user)
    monkeypatch.setattr(tenant_routes, "user_client", fake_user)
    monkeypatch.setattr(tenant_routes, "tenant_client", fake_tenant)
    monkeypatch.setattr(role_routes, "role_client", fake_role)
    monkeypatch.setattr("app.infrastructure.clients.user_client.user_client", fake_user)
    monkeypatch.setattr("app.infrastructure.clients.user_client.tenant_client", fake_tenant)
    monkeypatch.setattr("app.infrastructure.clients.user_client.role_client", fake_role)
    return fake_user, fake_tenant, fake_role


@pytest.fixture()
def client(fake_clients, monkeypatch):
    import shared.services

    monkeypatch.setattr(shared.services, "create_service_client", lambda name: FakeServiceClient())
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()
    auth_routes.rate_limit_storage.clear()


@pytest.fixture()
def auth_headers():
    token = auth_routes.create_access_token(
        {
            "sub": "user-1",
            "email": "user@example.com",
            "tenant_id": "tenant-1",
            "active_organization_id": "org-1",
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_monitoring_endpoints(client):
    for path in ["/health", "/readiness", "/liveness", "/startup", "/metrics"]:
        response = client.get(path)
        assert response.status_code == 200
    assert "dependencies" in client.get("/health").json()
    assert "cde_api_info" in client.get("/metrics").text


def test_bob_cloud_auth_routes_delegate_and_preserve_cookie(client):
    fake_bob_cloud = FakeBobCloudClient()
    main.app.dependency_overrides[bob_cloud_auth_routes.get_bob_cloud_client_for_request] = lambda: fake_bob_cloud

    session = client.get(
        "/api/auth/v1/session",
        headers={"Cookie": "bob_cloud_session=old", "X-Request-Id": "req-1"},
    )
    refresh = client.post("/api/auth/v1/refresh", headers={"X-Request-Id": "req-2"})
    logout = client.post("/api/auth/v1/logout", headers={"X-Request-Id": "req-3"})

    assert session.status_code == 200
    assert session.json()["authenticated"] is True
    assert "httponly" in session.headers["set-cookie"].lower()
    assert refresh.json()["authenticated"] is True
    assert logout.json()["authenticated"] is False
    assert fake_bob_cloud.calls[0][0] == "session"
    assert fake_bob_cloud.calls[0][1]["cookie"] == "bob_cloud_session=old"
    assert fake_bob_cloud.calls[0][1]["x-request-id"] == "req-1"
    assert [call[0] for call in fake_bob_cloud.calls] == ["session", "refresh", "logout"]


def test_local_dev_session_uses_local_jwt_without_bob_cloud(client, auth_headers, monkeypatch):
    def broken_factory():
        raise BobCloudModeError("Bob Cloud should not be required for local JWT sessions")

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("CDE_LOCAL_AUTH_ENABLED", raising=False)
    monkeypatch.setattr(bob_cloud_auth_routes, "create_bob_cloud_client_from_env", broken_factory)

    session = client.get("/api/auth/v1/session", headers=auth_headers)

    assert session.status_code == 200
    payload = session.json()
    assert payload["authenticated"] is True
    assert payload["source"] == "local-dev"
    assert payload["user"]["email"] == "user@example.com"
    assert payload["tenant"]["id"] == "tenant-1"
    assert "admin" in payload["platform_roles"]
    assert payload["permissions"] == ["users:manage"]


def test_local_dev_session_without_bearer_returns_unauthenticated_when_bob_cloud_unconfigured(client, monkeypatch):
    def broken_factory():
        raise BobCloudModeError("BOB_CLOUD_API_URL is required when BOB_CLOUD_MODE=real")

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("CDE_LOCAL_AUTH_ENABLED", raising=False)
    monkeypatch.setattr(bob_cloud_auth_routes, "create_bob_cloud_client_from_env", broken_factory)

    session = client.get("/api/auth/v1/session")

    assert session.status_code == 200
    assert session.json() == {"authenticated": False, "source": "local-dev"}


def test_local_jwt_session_is_refused_outside_dev_without_flag(client, auth_headers, monkeypatch):
    def broken_factory():
        raise BobCloudModeError("BOB_CLOUD_API_URL is required when BOB_CLOUD_MODE=real")

    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.delenv("CDE_LOCAL_AUTH_ENABLED", raising=False)
    monkeypatch.setattr(bob_cloud_auth_routes, "create_bob_cloud_client_from_env", broken_factory)

    session = client.get("/api/auth/v1/session", headers=auth_headers)

    assert session.status_code == 503
    assert session.json()["detail"]["code"] == "bob_cloud_unconfigured"


def test_local_jwt_session_can_be_explicitly_enabled_outside_dev(client, auth_headers, monkeypatch):
    def broken_factory():
        raise BobCloudModeError("Bob Cloud should not be required when local fallback is explicitly enabled")

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CDE_LOCAL_AUTH_ENABLED", "true")
    monkeypatch.setattr(bob_cloud_auth_routes, "create_bob_cloud_client_from_env", broken_factory)

    session = client.get("/api/auth/v1/session", headers=auth_headers)

    assert session.status_code == 200
    assert session.json()["source"] == "local-dev"


def test_bob_cloud_auth_routes_map_bob_cloud_errors(client):
    class FailingBobCloudClient:
        async def get_session_response(self, forward_headers=None):
            raise BobCloudResponseError(
                status_code=403,
                detail={"code": "capability_denied"},
                path="/api/auth/v1/session",
                method="GET",
            )

    main.app.dependency_overrides[bob_cloud_auth_routes.get_bob_cloud_client_for_request] = lambda: FailingBobCloudClient()

    response = client.get("/api/auth/v1/session")

    assert response.status_code == 403
    assert response.json()["detail"] == {"code": "capability_denied"}


def test_bob_cloud_client_dependency_maps_configuration_error():
    def broken_factory():
        raise BobCloudModeError("BOB_CLOUD_API_URL is required when BOB_CLOUD_MODE=real")

    original_factory = bob_cloud_auth_routes.create_bob_cloud_client_from_env
    bob_cloud_auth_routes.create_bob_cloud_client_from_env = broken_factory
    try:
        response = bob_cloud_auth_routes.get_bob_cloud_client()
    except Exception as exc:
        mapped = exc
    finally:
        bob_cloud_auth_routes.create_bob_cloud_client_from_env = original_factory

    assert mapped.status_code == 503
    assert mapped.detail["code"] == "bob_cloud_unconfigured"


def test_auth_register_login_refresh_and_profile(client, auth_headers):
    register = client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "correct-password", "first_name": "New", "last_name": "User"},
    )
    assert register.status_code == 201
    assert register.json()["email"] == "new@example.com"

    duplicate = client.post(
        "/auth/register",
        json={"email": "user@example.com", "password": "correct-password", "first_name": "Ada", "last_name": "Lovelace"},
    )
    assert duplicate.status_code == 400

    login = client.post("/auth/login", json={"email": "user@example.com", "password": "correct-password"})
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    access_payload = auth_routes.verify_token(tokens["access_token"])
    assert access_payload["role"] == "admin"
    assert access_payload["is_super_admin"] is True

    failed_login = client.post("/auth/login", json={"email": "user@example.com", "password": "wrong-password"})
    assert failed_login.status_code == 401

    refreshed = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["token_type"] == "bearer"
    refreshed_payload = auth_routes.verify_token(refreshed.json()["access_token"])
    assert refreshed_payload["role"] == "admin"
    assert refreshed_payload["is_super_admin"] is True

    me = client.get("/auth/me", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["id"] == "user-1"

    active_org = client.put("/auth/me/active-organization", json={"organization_id": "org-2"}, headers=auth_headers)
    assert active_org.status_code == 200
    assert active_org.json()["active_organization_id"] == "org-2"


def test_user_routes_delegate_to_user_backend(client, auth_headers):
    assert client.put("/users/me", json={"first_name": "Grace"}, headers=auth_headers).json()["first_name"] == "Grace"
    listed = client.get("/users", params={"skip": 2, "limit": 3}, headers=auth_headers).json()
    assert listed["skip"] == 2

    created = client.post(
        "/users",
        json={"email": "member@example.com", "password": "correct-password", "first_name": "Member", "last_name": "One"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    assert created.json()["email"] == "member@example.com"

    assert client.patch("/users/user-2", json={"last_name": "Updated"}, headers=auth_headers).json()["last_name"] == "Updated"
    assert client.delete("/users/user-2", headers=auth_headers).status_code == 204
    assert client.delete("/users/user-1", headers=auth_headers).status_code == 400
    assert client.delete("/users/missing", headers=auth_headers).status_code == 404


def test_tenant_admin_routes(client, auth_headers):
    tenants = client.get("/admin/tenants/", params={"status": "ACTIVE", "skip": 1}, headers=auth_headers)
    assert tenants.status_code == 200
    assert tenants.json()["total"] == 1

    assert client.get("/admin/tenants/tenant-1", headers=auth_headers).json()["id"] == "tenant-1"
    assert client.get("/admin/tenants/missing", headers=auth_headers).status_code == 404

    created = client.post(
        "/admin/tenants/",
        json={"name": "New Tenant", "slug": "new-tenant", "owner_email": "owner@example.com", "owner_name": "Owner"},
        headers=auth_headers,
    )
    assert created.status_code == 201

    assert client.patch("/admin/tenants/tenant-1", json={"plan": "ENTERPRISE"}, headers=auth_headers).json()["plan"] == "ENTERPRISE"
    assert client.delete("/admin/tenants/missing", headers=auth_headers).status_code == 404

    provisioned = client.post(
        "/admin/tenants/tenant-1/provision",
        json={
            "admin_email": "admin@example.com",
            "admin_password": "correct-password",
            "admin_first_name": "Admin",
            "admin_last_name": "User",
        },
        headers=auth_headers,
    )
    assert provisioned.status_code == 201
    assert provisioned.json()["tenant_id"] == "tenant-1"


def test_role_routes(client, auth_headers):
    assert client.get("/roles/permissions", headers=auth_headers).json()[0]["resource"] == "users"
    assert client.get("/roles", headers=auth_headers).json()["total"] == 1
    assert client.post("/roles", json={"name": "support"}, headers=auth_headers).status_code == 201
    assert client.get("/roles/role-admin", headers=auth_headers).json()["id"] == "role-admin"
    assert client.get("/roles/missing", headers=auth_headers).status_code == 404
    assert client.patch("/roles/role-admin", json={"name": "owner"}, headers=auth_headers).json()["name"] == "owner"
    assert client.put("/roles/role-admin/permissions", json={"permission_ids": ["perm-users"]}, headers=auth_headers).status_code == 200
    assert client.get("/roles/users/user-1/roles", headers=auth_headers).json()["roles"][0]["name"] == "admin"
    assert client.post("/roles/users/user-1/roles", json={"role_id": "role-admin"}, headers=auth_headers).status_code == 201
    assert client.delete("/roles/users/user-1/roles/role-admin", headers=auth_headers).status_code == 204
    assert client.delete("/roles/missing", headers=auth_headers).status_code == 404


def test_token_helpers_and_auth_dependency(fake_clients):
    access = auth_routes.create_access_token({"sub": "user-1", "email": "user@example.com"})
    refresh = auth_routes.create_refresh_token({"sub": "user-1"})
    assert auth_routes.verify_token(access)["type"] == "access"
    assert auth_routes.verify_token(refresh)["type"] == "refresh"
    assert auth_routes.verify_token("not-a-token") is None


@pytest.mark.asyncio
async def test_backend_client_methods_cover_paths(monkeypatch):
    fake_service = FakeServiceClient()
    monkeypatch.setattr("app.infrastructure.clients.user_client.create_service_client", lambda name: fake_service)

    user_client = UserClient()
    tenant_client = TenantClient()
    role_client = RoleClient()

    assert await user_client.get_by_id("missing") is None
    assert (await user_client.get_by_id("user-1"))["id"] == "user-1"
    assert await user_client.get_by_email("missing@example.com") is None
    assert (await user_client.create({"email": "created@example.com"}))["email"] == "created@example.com"
    assert (await user_client.update("user-1", {"first_name": "Updated"}))["first_name"] == "Updated"
    assert await user_client.delete("user-1") is True
    assert (await user_client.list_users(1, 2))["limit"] == 50
    assert (await user_client.get_user_roles("user-1"))[0]["name"] == "admin"
    assert (await user_client.get_user_permissions("user-1")) == ["users:manage"]

    assert await tenant_client.get_by_id("missing") is None
    assert (await tenant_client.get_by_id("tenant-1"))["id"] == "tenant-1"
    assert (await tenant_client.get_by_slug("croo"))["slug"] == "croo"
    assert (await tenant_client.create({"name": "Tenant"}))["name"] == "Tenant"
    assert (await tenant_client.update("tenant-1", {"plan": "TEAM"}))["plan"] == "TEAM"
    assert await tenant_client.delete("tenant-1") is True
    assert (await tenant_client.list_tenants("croo", "ACTIVE", 1, 2))["id"] == "tenant-1"

    assert (await role_client.list_roles())["name"] == "admin"
    assert (await role_client.create_role({"name": "support"}))["name"] == "support"
    assert await role_client.get_role("missing") is None
    assert (await role_client.get_role("role-admin"))["id"] == "role-admin"
    assert (await role_client.update_role("role-admin", {"name": "owner"}))["name"] == "owner"
    assert await role_client.delete_role("role-admin") is True
    assert (await role_client.set_permissions("role-admin", ["perm-users"]))["id"] == "role-admin"
    assert (await role_client.list_permissions())[0]["resource"] == "users"
    await role_client.assign_role("user-1", "role-admin")
    await role_client.remove_role("user-1", "role-admin")


def test_python_package_contract_loads_runtime_components():
    from auth_b4f_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (auth_routes, user_routes, tenant_routes, role_routes)
    assert contract.load_runtime_client_classes() == (UserClient, TenantClient, RoleClient)
