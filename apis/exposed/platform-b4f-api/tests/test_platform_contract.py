from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.infrastructure.clients.platform_clients import UsageClient, WorkflowClient
from app.middleware.auth import get_current_user, settings
from app.presentation.routes import (
    bob_settings_preferences_routes,
    bob_settings_security_routes,
    enrichment_routes,
    entitlement_routes,
    overview_routes,
    usage_routes,
    workflow_routes,
)
from shared.services import BobCloudModeError, BobCloudResponseError


class FakeWorkflowClient:
    async def list(self, skip=0, limit=50, level=None, module=None, is_template=None, forward_headers=None):
        return {"skip": skip, "limit": limit, "level": level, "module": module, "is_template": is_template}

    async def create(self, data, forward_headers=None):
        return {"id": "wf-new", **data}

    async def get(self, wf_id, forward_headers=None):
        if wf_id == "missing":
            return None
        if wf_id == "locked":
            return {"id": wf_id, "name": "Locked", "level": "company", "is_overridable": False}
        return {
            "id": wf_id,
            "name": "Workflow",
            "level": "company",
            "is_overridable": True,
            "trigger_type": "manual",
            "steps": [{"id": "step-1"}],
        }

    async def update(self, wf_id, data, forward_headers=None):
        return {"id": wf_id, **data}

    async def delete(self, wf_id, forward_headers=None):
        return True

    async def list_steps(self, wf_id, forward_headers=None):
        return [{"workflow_id": wf_id, "id": "step-1"}]

    async def add_step(self, wf_id, data, forward_headers=None):
        return {"workflow_id": wf_id, "id": "step-new", **data}

    async def update_step(self, wf_id, step_id, data, forward_headers=None):
        return {"workflow_id": wf_id, "id": step_id, **data}

    async def delete_step(self, wf_id, step_id, forward_headers=None):
        return True

    async def create_execution(self, wf_id, data, forward_headers=None):
        return {"workflow_id": wf_id, "execution_id": "exe-new", **data}

    async def list_executions(self, wf_id, limit=20, forward_headers=None):
        return [{"workflow_id": wf_id, "limit": limit}]

    async def get_execution(self, wf_id, exe_id, forward_headers=None):
        if exe_id == "missing":
            return None
        return {"workflow_id": wf_id, "execution_id": exe_id}

    async def get_monitoring_stats(self, forward_headers=None):
        return {"runs": 4}

    async def get_recent_executions(self, limit=20, status_filter=None, forward_headers=None):
        return [{"limit": limit, "status": status_filter}]


class FakeUsageClient:
    async def list(self, skip=0, limit=50, service_type=None, billing_category=None, user_id=None, date_from=None, date_to=None, forward_headers=None):
        return {
            "skip": skip,
            "limit": limit,
            "service_type": service_type,
            "billing_category": billing_category,
            "user_id": user_id,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
        }

    async def get_summary(self, date_from=None, date_to=None, forward_headers=None):
        return {"summary": True, "date_from": str(date_from) if date_from else None}

    async def admin_list(self, tenant_id=None, skip=0, limit=50, service_type=None, billing_category=None, user_id=None, date_from=None, date_to=None, forward_headers=None):
        return {"tenant_id": tenant_id, "skip": skip, "limit": limit, "service_type": service_type}

    async def admin_summary(self, tenant_id, date_from=None, date_to=None, forward_headers=None):
        return {"tenant_id": tenant_id, "summary": True}

    async def admin_by_intent(self, tenant_id=None, skip=0, limit=50, forward_headers=None):
        return {"tenant_id": tenant_id, "skip": skip, "limit": limit}

    async def admin_intent_detail(self, correlation_id, forward_headers=None):
        return {"correlation_id": correlation_id}


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


class FakeBobCloudClient:
    def __init__(self):
        self.calls = []

    async def get_entitlements(self, forward_headers=None):
        self.calls.append(("entitlements", dict(forward_headers or {})))
        return {
            "tenant_id": "tenant-croo-local",
            "user_id": "user-alex-local",
            "module_entitlements": {"bob_chat": "enabled", "bob_cockpit": "enabled"},
            "capabilities": [
                {"code": "bob_chat.use", "status": "enabled", "remaining": 100, "limit": 100}
            ],
        }

    async def check_capability(self, capability, forward_headers=None):
        self.calls.append(("check", capability, dict(forward_headers or {})))
        status_value = "enabled" if capability == "bob_chat.use" else "denied"
        return {"capability": capability, "status": status_value}

    async def list_tenants(self, forward_headers=None):
        self.calls.append(("tenants", dict(forward_headers or {})))
        return {"items": [{"id": "tenant-croo-local", "name": "Croo Local"}]}

    async def update_tenant(self, tenant_id, payload, idempotency_key, forward_headers=None):
        self.calls.append(("tenant_update", tenant_id, payload, idempotency_key, dict(forward_headers or {})))
        return {"id": tenant_id, **payload}

    async def list_licenses(self, forward_headers=None):
        self.calls.append(("licenses", dict(forward_headers or {})))
        return {
            "items": [
                {"code": "bob_chat.use", "status": "enabled", "remaining": 100, "limit": 100}
            ]
        }

    async def update_license(self, capability, payload, idempotency_key, forward_headers=None):
        self.calls.append(("license_update", capability, payload, idempotency_key, dict(forward_headers or {})))
        return {"code": capability, **payload}

    async def list_users(self, forward_headers=None):
        self.calls.append(("users", dict(forward_headers or {})))
        return {"items": [{"id": "user-alex-local", "email": "alexandre.local@croo.digital"}]}

    async def create_invitation(self, payload, idempotency_key, forward_headers=None):
        self.calls.append(("invite", payload, idempotency_key, dict(forward_headers or {})))
        return {"id": "invite-1", **payload}

    async def list_roles(self, forward_headers=None):
        self.calls.append(("roles", dict(forward_headers or {})))
        return {"items": [{"id": "role-admin", "code": "admin"}]}

    async def list_memberships(self, forward_headers=None):
        self.calls.append(("memberships", dict(forward_headers or {})))
        return {"items": [{"id": "membership-local-admin", "role_codes": ["admin"]}]}

    async def update_membership(self, membership_id, payload, idempotency_key, forward_headers=None):
        self.calls.append(("membership_update", membership_id, payload, idempotency_key, dict(forward_headers or {})))
        return {"id": membership_id, **payload}


@pytest.fixture()
def client(monkeypatch):
    main.app.dependency_overrides[workflow_routes.get_current_user] = lambda: {"user_id": "user-1"}
    main.app.dependency_overrides[usage_routes.get_current_user] = lambda: {"user_id": "user-1"}
    main.app.dependency_overrides[enrichment_routes.get_current_user] = lambda: {"user_id": "user-1"}
    main.app.dependency_overrides[overview_routes.get_current_user] = lambda: {"user_id": "user-1", "tenant_id": "tenant-1"}
    monkeypatch.setattr(workflow_routes, "workflow_client", FakeWorkflowClient())
    monkeypatch.setattr(usage_routes, "usage_client", FakeUsageClient())
    monkeypatch.setattr(
        overview_routes,
        "overview_service",
        overview_routes.PlatformOverviewService(FakeWorkflowClient(), FakeUsageClient()),
    )
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


def test_monitoring_endpoints(client):
    for path in ["/health", "/readiness", "/liveness", "/startup", "/metrics"]:
        response = client.get(path)
        assert response.status_code == 200
    assert "dependencies" in client.get("/health").json()
    assert "cde_api_info" in client.get("/metrics").text


def test_entitlement_routes_delegate_to_bob_cloud(client):
    fake_bob_cloud = FakeBobCloudClient()
    main.app.dependency_overrides[entitlement_routes.get_bob_cloud_client] = lambda: fake_bob_cloud

    entitlements = client.get(
        "/api/platform/v1/entitlements/me",
        headers={"Cookie": "bob_cloud_session=abc", "X-Request-Id": "req-1"},
    )
    check_query = client.get(
        "/api/platform/v1/entitlements/check",
        params={"capability": "bob_chat.use"},
        headers={"X-Request-Id": "req-2"},
    )
    check_post = client.post(
        "/api/platform/v1/entitlements/check",
        json={"capability": "agent.voice.customer_experience"},
        headers={"X-Request-Id": "req-3"},
    )

    assert entitlements.status_code == 200
    assert entitlements.json()["module_entitlements"]["bob_chat"] == "enabled"
    assert check_query.json() == {"capability": "bob_chat.use", "status": "enabled"}
    assert check_post.json() == {"capability": "agent.voice.customer_experience", "status": "denied"}
    assert fake_bob_cloud.calls[0][0] == "entitlements"
    assert fake_bob_cloud.calls[0][1]["cookie"] == "bob_cloud_session=abc"
    assert fake_bob_cloud.calls[1][1] == "bob_chat.use"
    assert fake_bob_cloud.calls[2][1] == "agent.voice.customer_experience"


def test_entitlement_routes_map_bob_cloud_errors(client):
    class FailingBobCloudClient:
        async def get_entitlements(self, forward_headers=None):
            raise BobCloudResponseError(
                status_code=403,
                detail={"code": "license_missing"},
                path="/api/platform/v1/entitlements/me",
                method="GET",
            )

    main.app.dependency_overrides[entitlement_routes.get_bob_cloud_client] = lambda: FailingBobCloudClient()

    response = client.get("/api/platform/v1/entitlements/me")

    assert response.status_code == 403
    assert response.json()["detail"] == {"code": "license_missing"}


def test_bob_settings_security_routes_delegate_to_bob_cloud(client):
    fake_bob_cloud = FakeBobCloudClient()
    main.app.dependency_overrides[bob_settings_security_routes.get_bob_cloud_client] = lambda: fake_bob_cloud

    tenants = client.get(
        "/api/bob-settings/v1/security/tenants",
        headers={"X-Request-Id": "req-tenants"},
    )
    tenant_update = client.patch(
        "/api/bob-settings/v1/security/tenants/tenant-croo-local",
        json={"name": "Croo Local QA"},
        headers={"Idempotency-Key": "tenant-1"},
    )
    licenses = client.get(
        "/api/bob-settings/v1/security/licenses",
        headers={"X-Request-Id": "req-licenses"},
    )
    license_update = client.patch(
        "/api/bob-settings/v1/security/licenses/bob_chat.use",
        json={"status": "disabled"},
        headers={"Idempotency-Key": "license-1"},
    )
    users = client.get(
        "/api/bob-settings/v1/security/users",
        headers={"Cookie": "bob_cloud_session=abc", "X-Request-Id": "req-users"},
    )
    roles = client.get("/api/bob-settings/v1/security/roles")
    memberships = client.get("/api/bob-settings/v1/security/memberships")
    invite = client.post(
        "/api/bob-settings/v1/security/invitations",
        json={"email": "new@example.com"},
        headers={"Idempotency-Key": "invite-1"},
    )
    membership_update = client.patch(
        "/api/bob-settings/v1/security/memberships/membership-local-admin",
        json={"role_codes": ["support"]},
        headers={"Idempotency-Key": "membership-1"},
    )

    assert tenants.json()["items"][0]["id"] == "tenant-croo-local"
    assert tenant_update.json()["name"] == "Croo Local QA"
    assert licenses.json()["items"][0]["code"] == "bob_chat.use"
    assert license_update.json()["status"] == "disabled"
    assert users.status_code == 200
    assert users.json()["items"][0]["id"] == "user-alex-local"
    assert roles.json()["items"][0]["code"] == "admin"
    assert memberships.json()["items"][0]["id"] == "membership-local-admin"
    assert invite.json()["email"] == "new@example.com"
    assert membership_update.json()["role_codes"] == ["support"]
    assert fake_bob_cloud.calls[0][0] == "tenants"
    assert fake_bob_cloud.calls[1][0] == "tenant_update"
    assert fake_bob_cloud.calls[1][3] == "tenant-1"
    assert fake_bob_cloud.calls[3][0] == "license_update"
    assert fake_bob_cloud.calls[3][3] == "license-1"
    assert fake_bob_cloud.calls[4][0] == "users"
    assert fake_bob_cloud.calls[4][1]["cookie"] == "bob_cloud_session=abc"
    assert fake_bob_cloud.calls[7][2] == "invite-1"
    assert fake_bob_cloud.calls[8][3] == "membership-1"


def test_bob_settings_gateway_rewritten_internal_paths_are_supported(client):
    fake_bob_cloud = FakeBobCloudClient()
    main.app.dependency_overrides[bob_settings_security_routes.get_bob_cloud_client] = lambda: fake_bob_cloud

    conversation = client.get("/conversation")
    voice = client.get("/voice")
    tenants = client.get("/security/tenants")

    assert conversation.status_code == 200
    assert conversation.json()["personality"]["tone"] == "professional"
    assert voice.status_code == 200
    assert voice.json()["voice"]["voice"] == "autumn"
    assert tenants.status_code == 200
    assert tenants.json()["items"][0]["id"] == "tenant-croo-local"
    assert fake_bob_cloud.calls[0][0] == "tenants"


def test_bob_runtime_settings_catalog_and_mutations(client):
    headers = {
        "Authorization": "Bearer local-admin-token",
        "X-CDE-Capabilities": "bob_settings.manage",
    }

    catalog = client.get("/api/bob-settings/v1/runtime", headers=headers)
    agent = client.post(
        "/api/bob-settings/v1/runtime/agents",
        json={"name": "Bob QA", "description": "Agent de verification"},
        headers={**headers, "Idempotency-Key": "agent-1"},
    )
    skill = client.post(
        "/api/bob-settings/v1/runtime/skills",
        json={"name": "Review Discipline", "scope": "shared_clean"},
        headers={**headers, "Idempotency-Key": "skill-1"},
    )
    tool = client.post(
        "/api/bob-settings/v1/runtime/tools",
        json={"name": "factory_status", "family": "factory", "risk": "read"},
        headers={**headers, "Idempotency-Key": "tool-1"},
    )
    replay = client.post(
        "/api/bob-settings/v1/runtime/tools",
        json={"name": "factory_status", "family": "factory", "risk": "read"},
        headers={**headers, "Idempotency-Key": "tool-1"},
    )
    missing_name = client.post(
        "/api/bob-settings/v1/runtime/skills",
        json={"description": "bad"},
        headers={**headers, "Idempotency-Key": "skill-bad"},
    )

    assert catalog.status_code == 200
    assert catalog.json()["providers"][0]["status"] == "runtime_backend_managed"
    assert catalog.json()["providers"][0]["model"] == "accounts/fireworks/models/kimi-k2p7-code"
    assert catalog.json()["agents"][0]["name"] == "Bob Orchestrator"
    assert agent.status_code == 201
    assert agent.json()["item"]["name"] == "Bob QA"
    assert skill.status_code == 201
    assert skill.json()["item"]["name"] == "Review Discipline"
    assert tool.status_code == 201
    assert tool.json()["item"]["family"] == "factory"
    assert replay.json() == tool.json()
    assert missing_name.status_code == 422
    assert missing_name.json()["detail"] == {"code": "name_required"}


def test_bob_settings_security_mutations_require_idempotency_key(client):
    fake_bob_cloud = FakeBobCloudClient()
    main.app.dependency_overrides[bob_settings_security_routes.get_bob_cloud_client] = lambda: fake_bob_cloud

    invite = client.post("/api/bob-settings/v1/security/invitations", json={"email": "new@example.com"})
    tenant_update = client.patch(
        "/api/bob-settings/v1/security/tenants/tenant-croo-local",
        json={"name": "Croo Local QA"},
    )
    license_update = client.patch(
        "/api/bob-settings/v1/security/licenses/bob_chat.use",
        json={"status": "disabled"},
    )
    membership_update = client.patch(
        "/api/bob-settings/v1/security/memberships/membership-local-admin",
        json={"role_codes": ["support"]},
    )

    assert invite.status_code == 422
    assert tenant_update.status_code == 422
    assert license_update.status_code == 422
    assert membership_update.status_code == 422
    assert fake_bob_cloud.calls == []


def test_bob_settings_security_cors_allows_idempotency_key(client):
    response = client.options(
        "/api/bob-settings/v1/security/licenses/bob_chat.use",
        headers={
            "Origin": "http://localhost:4200",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4200"
    assert "idempotency-key" in response.headers["access-control-allow-headers"].lower()


def test_bob_settings_preferences_are_local_and_idempotent(client):
    conversation = client.get("/api/bob-settings/v1/conversation")
    voice = client.get("/api/bob-settings/v1/voice")
    auth_headers = {
        "Authorization": "Bearer local-settings-session",
        "Idempotency-Key": "settings-conversation-1",
    }
    voice_headers = {
        "Authorization": "Bearer local-settings-session",
        "Idempotency-Key": "settings-voice-1",
    }

    assert conversation.status_code == 200
    assert conversation.json()["personality"]["tone"] == "professional"
    assert voice.status_code == 200
    assert voice.json()["voice"]["voice"] == "autumn"

    updated_conversation = client.put(
        "/api/bob-settings/v1/conversation",
        json={"personality": {"tone": "friendly", "language": "fr"}},
        headers=auth_headers,
    )
    updated_voice = client.put(
        "/api/bob-settings/v1/voice",
        json={"voice": {"voice": "marie", "speed": 1.2, "auto_listen": False}},
        headers=voice_headers,
    )
    replay_conversation = client.put(
        "/api/bob-settings/v1/conversation",
        json={"personality": {"tone": "friendly", "language": "fr"}},
        headers=auth_headers,
    )
    conflicting_replay = client.put(
        "/api/bob-settings/v1/conversation",
        json={"personality": {"tone": "direct"}},
        headers=auth_headers,
    )
    scoped_conversation = client.get(
        "/api/bob-settings/v1/conversation",
        headers={"Authorization": "Bearer another-local-settings-session"},
    )

    assert updated_conversation.status_code == 200
    assert updated_conversation.json()["personality"]["tone"] == "friendly"
    assert updated_conversation.json()["personality"]["language"] == "fr"
    assert updated_voice.status_code == 200
    assert updated_voice.json()["voice"]["voice"] == "marie"
    assert updated_voice.json()["voice"]["auto_listen"] is False
    assert replay_conversation.status_code == 200
    assert replay_conversation.json() == updated_conversation.json()
    assert conflicting_replay.status_code == 409
    assert conflicting_replay.json()["detail"]["code"] == "idempotency_conflict"
    assert scoped_conversation.json()["personality"]["tone"] == "professional"


def test_bob_settings_preferences_mutations_require_idempotency_key(client):
    conversation = client.put(
        "/api/bob-settings/v1/conversation",
        json={"personality": {"tone": "friendly"}},
        headers={"Authorization": "Bearer local-settings-session"},
    )
    voice = client.put(
        "/api/bob-settings/v1/voice",
        json={"voice": {"voice": "marie"}},
        headers={"Authorization": "Bearer local-settings-session"},
    )

    assert conversation.status_code == 422
    assert voice.status_code == 422


def test_bob_settings_preferences_mutations_require_local_session_and_capability(client, monkeypatch):
    no_session = client.put(
        "/api/bob-settings/v1/conversation",
        json={"personality": {"tone": "friendly"}},
        headers={"Idempotency-Key": "settings-conversation-session"},
    )

    monkeypatch.setenv("CDE_LOCAL_BOB_SETTINGS_CAPABILITIES", "bob_chat.use")
    no_capability = client.put(
        "/api/bob-settings/v1/voice",
        json={"voice": {"voice": "marie"}},
        headers={
            "Authorization": "Bearer local-settings-session",
            "Idempotency-Key": "settings-voice-capability",
        },
    )

    assert no_session.status_code == 401
    assert no_session.json()["detail"]["code"] == "session_required"
    assert no_capability.status_code == 403
    assert no_capability.json()["detail"]["code"] == "capability_denied"


def test_bob_settings_preferences_cors_allows_loopback_dev_origin(client):
    response = client.options(
        "/api/bob-settings/v1/conversation",
        headers={
            "Origin": "http://127.0.0.1:4300",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:4300"


def test_entitlement_dependency_maps_configuration_error():
    def broken_factory():
        raise BobCloudModeError("BOB_CLOUD_API_URL is required when BOB_CLOUD_MODE=real")

    original_factory = entitlement_routes.create_bob_cloud_client_from_env
    entitlement_routes.create_bob_cloud_client_from_env = broken_factory
    try:
        response = entitlement_routes.get_bob_cloud_client()
    except Exception as exc:
        mapped = exc
    finally:
        entitlement_routes.create_bob_cloud_client_from_env = original_factory

    assert mapped.status_code == 503
    assert mapped.detail["code"] == "bob_cloud_unconfigured"


def test_workflow_crud_and_steps(client):
    assert client.get("/workflows", params={"level": "company", "module": "crm", "is_template": True}).json()["is_template"] is True
    assert client.post("/workflows", json={"name": "Flow"}).status_code == 201
    assert client.get("/workflows/wf-1").json()["id"] == "wf-1"
    assert client.get("/workflows/missing").status_code == 404
    assert client.patch("/workflows/wf-1", json={"name": "Updated"}).json()["name"] == "Updated"
    assert client.delete("/workflows/wf-1").status_code == 204
    assert client.get("/workflows/wf-1/steps").json()[0]["id"] == "step-1"
    assert client.post("/workflows/wf-1/steps", json={"name": "Step"}).status_code == 201
    assert client.patch("/workflows/wf-1/steps/step-1", json={"name": "Updated"}).json()["id"] == "step-1"
    assert client.delete("/workflows/wf-1/steps/step-1").status_code == 204


def test_workflow_executions_monitoring_and_override(client):
    assert client.post("/workflows/wf-1/run", json={"input": {}}).status_code == 201
    assert client.get("/workflows/wf-1/executions", params={"limit": 4}).json()[0]["limit"] == 4
    assert client.get("/workflows/wf-1/executions/exe-1").json()["execution_id"] == "exe-1"
    assert client.get("/workflows/wf-1/executions/missing").status_code == 404
    assert client.get("/workflows/monitoring/stats").json()["runs"] == 4
    recent = client.get("/workflows/monitoring/recent", params={"limit": 3, "status": "success"}).json()
    assert recent[0]["status"] == "success"
    assert client.post("/workflows/wf-1/override", json={"target_level": "user", "new_name": "User Flow"}).status_code == 201
    assert client.post("/workflows/missing/override", json={"target_level": "user"}).status_code == 404
    assert client.post("/workflows/locked/override", json={"target_level": "user"}).status_code == 403
    assert client.post("/workflows/wf-1/override", json={"target_level": "system"}).status_code == 400


def test_usage_and_enrichment_routes(client):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    usage = client.get(
        "/usage",
        params={
            "skip": 1,
            "limit": 5,
            "service_type": "ai",
            "billing_category": "tokens",
            "user_id": "user-1",
            "date_from": now.isoformat(),
            "date_to": now.isoformat(),
        },
    ).json()
    assert usage["service_type"] == "ai"
    assert client.get("/usage/summary", params={"date_from": now.isoformat()}).json()["summary"] is True
    assert client.get("/admin/usage", params={"tenant_id": "tenant-1", "service_type": "ai"}).json()["tenant_id"] == "tenant-1"
    assert client.get("/admin/usage/summary", params={"tenant_id": "tenant-1"}).json()["summary"] is True
    assert client.get("/admin/usage/by-intent", params={"tenant_id": "tenant-1", "limit": 2}).json()["limit"] == 2
    assert client.get("/admin/usage/by-intent/corr-1").json()["correlation_id"] == "corr-1"
    assert client.post("/organizations/org-1/enrich").json()["status"] == "not_implemented"
    assert client.get("/organizations/org-1/enrich/status").json()["organization_id"] == "org-1"


def test_platform_overview_composes_workflow_and_usage(client):
    payload = client.get("/overview").json()
    assert payload["tenant_id"] == "tenant-1"
    assert payload["monitoring"] == {"runs": 4}
    assert payload["usage"]["summary"] is True
    assert payload["recent_executions"][0]["limit"] == 5
    assert payload["totals"] == {"workflows": 0, "recent_executions": 1}


def test_auth_dependency_accepts_valid_jwt():
    token = jwt.encode(
        {"sub": "user-1", "email": "user@example.com", "tenant_id": "tenant-1"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    credentials = type("Credentials", (), {"credentials": token})()
    user = get_current_user(credentials)
    assert user == {"user_id": "user-1", "email": "user@example.com", "tenant_id": "tenant-1"}


def test_auth_dependency_rejects_invalid_jwt():
    credentials = type("Credentials", (), {"credentials": "not-a-token"})()
    with pytest.raises(Exception) as exc_info:
        get_current_user(credentials)
    assert getattr(exc_info.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_backend_client_methods_cover_paths(monkeypatch):
    fake_workflow_service = FakeServiceClient()
    fake_usage_service = FakeServiceClient()

    def fake_factory(name):
        if name == "workflow~backend-api":
            return fake_workflow_service
        if name == "usage~backend-api":
            return fake_usage_service
        raise AssertionError(name)

    monkeypatch.setattr("app.infrastructure.clients.platform_clients.create_service_client", fake_factory)
    workflow_client = WorkflowClient()
    usage_client = UsageClient()

    assert (await workflow_client.list(1, 5, "company", "crm", True))["params"]["is_template"] == "true"
    assert (await workflow_client.create({"name": "Flow"}))["json"]["name"] == "Flow"
    assert await workflow_client.get("missing") is None
    assert (await workflow_client.get("wf-1"))["path"].endswith("/wf-1")
    assert (await workflow_client.update("wf-1", {"name": "Updated"}))["json"]["name"] == "Updated"
    assert await workflow_client.delete("wf-1") is True
    assert (await workflow_client.list_steps("wf-1"))["path"].endswith("/steps")
    assert (await workflow_client.add_step("wf-1", {"name": "Step"}))["json"]["name"] == "Step"
    assert (await workflow_client.update_step("wf-1", "step-1", {"name": "Updated"}))["path"].endswith("/step-1")
    assert await workflow_client.delete_step("wf-1", "step-1") is True
    assert (await workflow_client.create_execution("wf-1", {"input": {}}))["path"].endswith("/executions")
    assert (await workflow_client.list_executions("wf-1", 3))["params"] == {"limit": "3"}
    assert await workflow_client.get_execution("wf-1", "missing") is None
    assert (await workflow_client.get_execution("wf-1", "exe-1"))["path"].endswith("/exe-1")
    assert (await workflow_client.update_execution("wf-1", "exe-1", {"status": "done"}))["json"]["status"] == "done"
    assert (await workflow_client.get_monitoring_stats())["path"] == "/api/v1/workflows/monitoring/stats"
    assert (await workflow_client.get_recent_executions(2, "success"))["params"] == {"limit": "2", "status": "success"}

    assert (await usage_client.record({"service": "ai"}))["json"]["service"] == "ai"
    usage = await usage_client.list(1, 5, "ai", "tokens", "user-1", "from", "to")
    assert usage["params"]["service_type"] == "ai"
    assert (await usage_client.get_summary("from", "to"))["params"] == {"date_from": "from", "date_to": "to"}
    assert (await usage_client.admin_list("tenant-1", 1, 5, "ai", "tokens", "user-1", "from", "to"))["params"]["tenant_id"] == "tenant-1"
    assert (await usage_client.admin_summary("tenant-1", "from", "to"))["params"]["tenant_id"] == "tenant-1"
    assert (await usage_client.admin_by_intent("tenant-1", 1, 5))["params"] == {"skip": "1", "limit": "5", "tenant_id": "tenant-1"}
    assert (await usage_client.admin_intent_detail("corr-1"))["path"].endswith("/corr-1")
    assert (await usage_client.list_rate_cards(False))["params"] == {"active_only": "false"}
    assert (await usage_client.create_rate_card({"name": "Default"}))["json"]["name"] == "Default"


def test_python_package_contract_loads_runtime_components():
    from platform_b4f_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (overview_routes, workflow_routes, usage_routes, enrichment_routes)
    assert contract.load_runtime_client_classes() == (WorkflowClient, UsageClient)
