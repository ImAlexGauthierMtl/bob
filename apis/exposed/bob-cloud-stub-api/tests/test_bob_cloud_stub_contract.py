from fastapi.testclient import TestClient
import pytest

import main
from app.presentation.deps import reset_stub_fixture_source


@pytest.fixture(autouse=True)
def stub_env(monkeypatch):
    monkeypatch.setenv("BOB_CLOUD_MODE", "stub")
    monkeypatch.setenv("ENV", "test")
    reset_stub_fixture_source()


def client():
    return TestClient(main.app)


def test_session_sets_http_only_cookie():
    with client() as test_client:
        response = test_client.get("/api/auth/v1/session")

    assert response.status_code == 200
    payload = response.json()
    assert payload["authenticated"] is True
    assert payload["source"] == "bob-cloud-stub"
    assert payload["user"]["id"] == "user-alex-local"
    assert "httponly" in response.headers["set-cookie"].lower()


def test_entitlements_are_deterministic():
    with client() as test_client:
        response = test_client.get("/api/platform/v1/entitlements/me")

    assert response.status_code == 200
    capabilities = {item["code"]: item for item in response.json()["capabilities"]}
    assert capabilities["bob_chat.use"]["status"] == "enabled"
    assert capabilities["agent.voice.customer_experience"]["status"] == "disabled"


def test_capability_check_refuses_unknown_capability():
    with client() as test_client:
        response = test_client.post(
            "/api/platform/v1/entitlements/check",
            json={"capability": "unknown.capability"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "capability": "unknown.capability",
        "status": "denied",
        "reason_code": "capability_unknown",
    }


def test_refresh_logout_and_platform_lists_are_deterministic():
    with client() as test_client:
        refresh = test_client.post("/api/auth/v1/refresh")
        logout = test_client.post("/api/auth/v1/logout")
        tenant = test_client.get("/api/platform/v1/tenants/current")
        tenants = test_client.get("/api/platform/v1/tenants")
        licenses = test_client.get("/api/platform/v1/licenses")
        users = test_client.get("/api/iam/v1/users")
        roles = test_client.get("/api/iam/v1/roles")
        memberships = test_client.get("/api/iam/v1/memberships")
        capability = test_client.post(
            "/api/platform/v1/entitlements/check",
            json={"capability": "bob_chat.use"},
        )

    assert refresh.status_code == 200
    assert "httponly" in refresh.headers["set-cookie"].lower()
    assert logout.status_code == 200
    assert logout.json() == {"authenticated": False, "source": "bob-cloud-stub"}
    assert tenant.json()["id"] == "tenant-croo-local"
    assert tenants.json()["items"][0]["id"] == "tenant-croo-local"
    assert licenses.json()["items"][0]["source"] == "stub-license"
    assert users.json()["items"][0]["id"] == "user-alex-local"
    assert roles.json()["items"][0]["code"] == "admin"
    assert memberships.json()["items"][0]["id"] == "membership-local-admin"
    assert capability.json()["status"] == "enabled"


def test_local_platform_management_mutations_are_persistent_and_idempotent():
    with client() as test_client:
        tenant = test_client.patch(
            "/api/platform/v1/tenants/tenant-croo-local",
            json={"name": "Croo Local QA"},
            headers={"Idempotency-Key": "tenant-update-1"},
        )
        tenant_retry = test_client.patch(
            "/api/platform/v1/tenants/tenant-croo-local",
            json={"name": "Croo Local Drift"},
            headers={"Idempotency-Key": "tenant-update-1"},
        )
        license_update = test_client.patch(
            "/api/platform/v1/licenses/agent.voice.customer_experience",
            json={"status": "enabled", "remaining": 3, "limit": 5},
            headers={"Idempotency-Key": "license-update-1"},
        )
        invite = test_client.post(
            "/api/iam/v1/invitations",
            json={"email": "new@example.com", "role_codes": ["support"]},
            headers={"Idempotency-Key": "invite-1"},
        )
        invite_retry = test_client.post(
            "/api/iam/v1/invitations",
            json={"email": "different@example.com", "role_codes": ["admin"]},
            headers={"Idempotency-Key": "invite-1"},
        )
        membership = test_client.patch(
            "/api/iam/v1/memberships/membership-local-admin",
            json={"role_codes": ["support"]},
            headers={"Idempotency-Key": "membership-update-1"},
        )
        current_tenant = test_client.get("/api/platform/v1/tenants/current")
        entitlements = test_client.get("/api/platform/v1/entitlements/me")
        users = test_client.get("/api/iam/v1/users")
        memberships = test_client.get("/api/iam/v1/memberships")

    assert tenant.status_code == 200
    assert tenant.json()["name"] == "Croo Local QA"
    assert tenant_retry.json()["name"] == "Croo Local QA"
    assert current_tenant.json()["name"] == "Croo Local QA"
    assert license_update.json()["status"] == "enabled"
    assert license_update.json()["remaining"] == 3
    assert entitlements.json()["module_entitlements"]["customer_experience_agent"] == "enabled"
    assert invite.status_code == 200
    assert invite.json()["email"] == "new@example.com"
    assert invite_retry.json()["id"] == invite.json()["id"]
    assert invite_retry.json()["email"] == "new@example.com"
    assert users.json()["items"][-1]["email"] == "new@example.com"
    assert membership.json()["role_codes"] == ["support"]
    assert memberships.json()["items"][0]["role_codes"] == ["support"]


def test_local_platform_management_mutations_require_idempotency_key():
    with client() as test_client:
        tenant = test_client.patch(
            "/api/platform/v1/tenants/tenant-croo-local",
            json={"name": "No Key"},
        )
        license_update = test_client.patch(
            "/api/platform/v1/licenses/bob_chat.use",
            json={"status": "disabled"},
        )
        invite = test_client.post("/api/iam/v1/invitations", json={"email": "a@b.test"})
        membership = test_client.patch(
            "/api/iam/v1/memberships/membership-local-admin",
            json={},
        )

    assert tenant.status_code == 422
    assert license_update.status_code == 422
    assert invite.status_code == 422
    assert membership.status_code == 422


def test_local_platform_management_returns_stable_not_found_errors():
    with client() as test_client:
        tenant = test_client.patch(
            "/api/platform/v1/tenants/missing",
            json={"name": "Missing"},
            headers={"Idempotency-Key": "tenant-missing-1"},
        )
        license_update = test_client.patch(
            "/api/platform/v1/licenses/missing.capability",
            json={"status": "enabled"},
            headers={"Idempotency-Key": "license-missing-1"},
        )
        membership = test_client.patch(
            "/api/iam/v1/memberships/missing",
            json={"role_codes": ["support"]},
            headers={"Idempotency-Key": "membership-missing-1"},
        )

    assert tenant.status_code == 404
    assert tenant.json()["detail"]["code"] == "stub_resource_not_found"
    assert license_update.status_code == 404
    assert license_update.json()["detail"]["code"] == "stub_resource_not_found"
    assert membership.status_code == 404
    assert membership.json()["detail"]["code"] == "stub_resource_not_found"


def test_stub_refuses_production_mode(monkeypatch):
    monkeypatch.setenv("BOB_CLOUD_MODE", "stub")
    monkeypatch.setenv("ENV", "prod")

    with pytest.raises(RuntimeError, match="forbidden in production"):
        main.assert_stub_allowed()


def test_stub_requires_stub_mode(monkeypatch):
    monkeypatch.setenv("BOB_CLOUD_MODE", "real")
    monkeypatch.setenv("ENV", "test")

    with pytest.raises(RuntimeError, match="requires BOB_CLOUD_MODE=stub"):
        main.assert_stub_allowed()


def test_python_package_contract_loads_runtime_components():
    from bob_cloud_stub_api.contract import CONTRACT_VERSION, load_runtime_components

    assert CONTRACT_VERSION == "0.1.0"
    assert len(load_runtime_components()) == 4
