import os

from jose import jwt
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AGENT_BACKEND_API_URL", "http://agent-backend-api:9008")

import main
from app.application.use_cases.behavioral_analyzer import BehavioralAnalyzer
from app.infrastructure.clients.agent_client import (
    BccClient,
    ClientMapClient,
    ToolGovernanceClient,
    TrainingClient,
    create_agent_backend_client,
)
from app.middleware.auth import get_current_user, settings
from app.presentation.routes import (
    agent_control_routes,
    bcc_routes,
    client_map_routes,
    tool_governance_routes,
    training_routes,
)
from shared.infrastructure import InternalSessionContextSigner


def payload(method, *args, **extra):
    body = {"method": method, "args": list(args)}
    body.update(extra)
    return body


class FakeRouteClient:
    def __getattr__(self, name):
        async def method(*args, **kwargs):
            if name in {"get", "get_meddpicc_score"} and args and args[0] == "missing-id":
                return None
            if name.startswith("delete") or name.startswith("reset") or name.startswith("unlink") or name.startswith("remove"):
                return True
            return payload(name, *args)

        return method


class FakeBehaviorClientMap:
    def __init__(self):
        self.updated = []

    async def get(self, contact_id, forward_headers=None):
        return {
            "golden_notes": [
                {"emotional_climate": "POSITIVE", "interaction_type": "CALL", "verbatim": "Ready to move"}
            ],
            "role_type": "decision_maker",
            "trust_level": "high",
        }

    async def upsert(self, contact_id, data, forward_headers=None):
        self.updated.append((contact_id, data))
        return {"contact_id": contact_id, **data}


class FakeToolGovernanceRouteClient:
    def __init__(self):
        self.calls = []

    async def list_policies(self, headers):
        self.calls.append(("list_policies", headers))
        return {"items": [], "total": 0, "enabled_total": 0}

    async def update_policy(self, policy_id, data, headers):
        self.calls.append(("update_policy", policy_id, data, headers))
        return {"id": policy_id, **data}

    async def get_my_access(self, headers):
        self.calls.append(("get_my_access", headers))
        return {"preferences": {"preferred_email_provider": "auto"}, "allowed_tools": []}

    async def update_my_preferences(self, data, headers):
        self.calls.append(("update_my_preferences", data, headers))
        return {"preferred_email_provider": data.get("preferred_email_provider", "auto")}


class FakeResponse:
    def __init__(self, payload_data=None, status_code=200):
        self._payload = payload_data or {}
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
        if "missing-id" in path:
            return FakeResponse(status_code=404)
        return FakeResponse({"path": path, "params": params, "items": [{"path": path}]})

    async def post(self, path, json=None, forward_headers=None):
        self.calls.append(("post", path, json, forward_headers))
        if "/capabilities/check" in path:
            return FakeResponse({"granted": True, "path": path})
        return FakeResponse({"path": path, "json": json}, status_code=201)

    async def put(self, path, json=None, forward_headers=None):
        self.calls.append(("put", path, json, forward_headers))
        return FakeResponse({"path": path, "json": json})

    async def patch(self, path, json=None, forward_headers=None):
        self.calls.append(("patch", path, json, forward_headers))
        return FakeResponse({"path": path, "json": json})

    async def delete(self, path, forward_headers=None):
        self.calls.append(("delete", path, None, forward_headers))
        return FakeResponse(status_code=404 if "missing-id" in path else 204)


@pytest.fixture()
def client(monkeypatch):
    bcc = FakeRouteClient()
    client_map = FakeRouteClient()
    training = FakeRouteClient()
    tool_governance = FakeToolGovernanceRouteClient()

    monkeypatch.setattr(bcc_routes, "bcc_client", bcc)
    monkeypatch.setattr(client_map_routes, "client_map_client", client_map)
    monkeypatch.setattr(training_routes, "training_client", training)
    monkeypatch.setattr(tool_governance_routes, "tool_governance_client", tool_governance)

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers():
    token = jwt.encode(
        {
            "sub": "user-1",
            "email": "user@example.com",
            "tenant_id": "tenant-1",
            "type": "access",
            "permissions": ["agent_control.manage"],
        },
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


def test_agent_control_contract_is_authenticated_and_describes_public_surface(client, auth_headers):
    assert client.get("/agent-control/contract").status_code == 401

    response = client.get("/agent-control/contract", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["surface"] == "agent-control"
    assert body["public_base_path"] == "/api/agent-control/v1"
    assert body["frontend_environment_key"] == "agentControlApiUrl"
    assert body["backing_service"] == {
        "name": "agent-control-b4f-api",
        "status": "dedicated_service_extracted_implementation",
        "implementation_source": "agent-control-b4f-api",
    }
    assert body["identity"]["tenant_id_source"] == "session"
    assert body["identity"]["user_id_source"] == "session"
    assert body["identity"]["frontend_identity_override_allowed"] is False
    assert body["identity"]["session_validated"] is True
    assert {namespace["name"] for namespace in body["namespaces"]} == {"bcc", "training", "client-map", "tool-governance"}
    assert all(namespace["covers_existing_namespace"] for namespace in body["namespaces"] if namespace["name"] != "tool-governance")
    assert "frontend_to_b4f_only" in body["guards"]
    assert "no_tenant_or_user_from_frontend" in body["guards"]


def test_agent_control_routes_require_permission(client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CDE_LOCAL_AGENT_CONTROL_CAPABILITIES", "")
    token = jwt.encode(
        {"sub": "user-1", "email": "user@example.com", "tenant_id": "tenant-1", "type": "access"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    permitted_token = jwt.encode(
        {
            "sub": "user-1",
            "email": "user@example.com",
            "tenant_id": "tenant-1",
            "type": "access",
            "permissions": ["agent_control.manage"],
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    denied = client.get("/bcc/organizations", headers={"Authorization": f"Bearer {token}"})
    forged_header = client.get(
        "/bcc/organizations",
        headers={"Authorization": f"Bearer {token}", "X-CDE-Capabilities": "agent_control.manage"},
    )
    allowed = client.get("/bcc/organizations", headers={"Authorization": f"Bearer {permitted_token}"})

    assert denied.status_code == 403
    assert denied.json()["detail"] == {"code": "capability_denied", "capability": "agent_control.manage"}
    assert forged_header.status_code == 403
    assert allowed.status_code == 200


def test_agent_control_local_dev_capability_context(client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CDE_LOCAL_AGENT_CONTROL_CAPABILITIES", "")
    token = jwt.encode(
        {"sub": "user-1", "email": "user@example.com", "tenant_id": "tenant-1", "type": "access"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    denied = client.get("/bcc/organizations", headers={"Authorization": f"Bearer {token}"})
    allowed = client.get(
        "/bcc/organizations",
        headers={"Authorization": f"Bearer {token}", "X-CDE-Capabilities": "agent_control.manage"},
    )

    assert denied.status_code == 403
    assert allowed.status_code == 200


def test_agent_control_local_dev_env_capability_context(client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CDE_LOCAL_AGENT_CONTROL_CAPABILITIES", "agent_control.manage")
    token = jwt.encode(
        {"sub": "user-1", "email": "user@example.com", "tenant_id": "tenant-1", "type": "access"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get("/bcc/organizations", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


def test_agent_control_local_dev_accepts_converted_bcc_permissions(client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CDE_LOCAL_AGENT_CONTROL_CAPABILITIES", "")
    token = jwt.encode(
        {
            "sub": "user-1",
            "email": "user@example.com",
            "tenant_id": "tenant-1",
            "type": "access",
            "permissions": ["bcc:write"],
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get("/bcc/organizations", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


def test_agent_control_production_rejects_converted_bcc_permissions(client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CDE_LOCAL_AGENT_CONTROL_CAPABILITIES", "")
    token = jwt.encode(
        {
            "sub": "user-1",
            "email": "user@example.com",
            "tenant_id": "tenant-1",
            "type": "access",
            "permissions": ["bcc:write"],
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get("/bcc/organizations", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_agent_control_surface_mounts_only_its_public_namespaces():
    bounded_app = main.create_app()
    paths = set(bounded_app.openapi()["paths"])

    assert "/agent-control/contract" in paths
    assert "/bcc/organizations" in paths
    assert "/training/sessions" in paths
    assert "/contacts/{contact_id}/client-map" in paths
    assert "/tool-governance/policies" in paths
    assert "/tool-governance/me" in paths
    assert "/bob/chat" not in paths
    assert "/bob/settings" not in paths
    assert "/capabilities/catalog" not in paths


def test_bcc_routes(client, auth_headers):
    endpoints = [
        ("GET", "/bcc/organizations"),
        ("POST", "/bcc/organizations"),
        ("GET", "/bcc/organizations/org-1"),
        ("PUT", "/bcc/organizations/org-1"),
        ("DELETE", "/bcc/organizations/org-1"),
        ("PUT", "/bcc/organizations/org-1/profile"),
        ("GET", "/bcc/organizations/org-1/departments"),
        ("POST", "/bcc/organizations/org-1/departments"),
        ("DELETE", "/bcc/departments/dept-1"),
        ("GET", "/bcc/departments/dept-1/teams"),
        ("POST", "/bcc/departments/dept-1/teams"),
        ("DELETE", "/bcc/teams/team-1"),
        ("GET", "/bcc/industries"),
        ("GET", "/bcc/industries/industry-1"),
        ("POST", "/bcc/industries"),
        ("PUT", "/bcc/industries/industry-1"),
        ("DELETE", "/bcc/industries/industry-1"),
        ("GET", "/bcc/careers"),
        ("POST", "/bcc/careers"),
        ("DELETE", "/bcc/careers/career-1"),
        ("GET", "/bcc/skill-templates"),
        ("POST", "/bcc/skill-templates"),
        ("DELETE", "/bcc/skill-templates/template-1"),
        ("GET", "/bcc/task-templates"),
        ("POST", "/bcc/task-templates"),
        ("DELETE", "/bcc/task-templates/template-1"),
        ("GET", "/bcc/domains"),
        ("POST", "/bcc/domains"),
        ("DELETE", "/bcc/domains/domain-1"),
        ("GET", "/bcc/intents"),
        ("GET", "/bcc/intents/intent-1"),
        ("POST", "/bcc/intents"),
        ("DELETE", "/bcc/intents/intent-1"),
        ("GET", "/bcc/cognitive-map"),
        ("GET", "/bcc/organizations/org-1/regulations"),
        ("POST", "/bcc/organizations/org-1/regulations"),
        ("DELETE", "/bcc/regulations/reg-1"),
        ("POST", "/bcc/organizations/org-1/industries/industry-1"),
        ("DELETE", "/bcc/organizations/org-1/industries/industry-1"),
        ("GET", "/bcc/roles"),
        ("POST", "/bcc/roles"),
        ("GET", "/bcc/roles/role-1"),
        ("PUT", "/bcc/roles/role-1"),
        ("DELETE", "/bcc/roles/role-1"),
        ("GET", "/bcc/teams/team-1/roles"),
        ("POST", "/bcc/roles/role-1/skills"),
        ("PUT", "/bcc/skills/skill-1"),
        ("DELETE", "/bcc/skills/skill-1"),
        ("POST", "/bcc/roles/role-1/tasks"),
        ("PUT", "/bcc/tasks/task-1"),
        ("DELETE", "/bcc/tasks/task-1"),
        ("POST", "/bcc/tasks/task-1/steps"),
        ("POST", "/bcc/skills/skill-1/resources"),
        ("POST", "/bcc/roles/role-1/milestones"),
        ("POST", "/bcc/profiles/contact/contact-1/entries"),
        ("GET", "/bcc/profiles/contact/contact-1"),
        ("GET", "/bcc/profiles/contact/contact-1/history"),
        ("GET", "/bcc/profiles/contact/contact-1/summary"),
    ]
    for method, path in endpoints:
        response = client.request(method, path, headers=auth_headers, json={"name": "value"} if method in {"POST", "PUT"} else None)
        assert response.status_code in {200, 201, 204}, f"{method} {path}: {response.text}"


def test_training_and_client_map_routes(client, auth_headers):
    assert client.post("/training/sessions", json={"topic": "CRM"}, headers=auth_headers).status_code == 201
    assert client.patch("/training/sessions/session-1/slide", json={"slide": 2}, headers=auth_headers).json()["method"] == "update_slide"
    assert client.get("/training/sessions/session-1/notes", headers=auth_headers).json()["method"] == "get_notes"
    assert client.post("/training/sessions/session-1/notes", json={"note": "A"}, headers=auth_headers).status_code == 201
    assert client.delete("/training/notes/note-1", headers=auth_headers).status_code == 204
    assert client.get("/training/sessions/session-1/missing", headers=auth_headers).json()["method"] == "get_missing"
    assert client.post("/training/sessions/session-1/missing", json={"item": "X"}, headers=auth_headers).status_code == 201
    assert client.delete("/training/missing/item-1", headers=auth_headers).status_code == 204

    assert client.get("/contacts/contact-1/client-map", headers=auth_headers).json()["method"] == "get"
    assert client.get("/contacts/missing-id/client-map", headers=auth_headers).status_code == 404
    assert client.put("/contacts/contact-1/client-map", json={"role_type": "buyer"}, headers=auth_headers).json()["method"] == "upsert"
    assert client.post("/contacts/contact-1/client-map/golden-notes", json={"note": "A"}, headers=auth_headers).status_code == 201
    assert client.put("/contacts/contact-1/client-map/golden-notes/note-1", json={"note": "B"}, headers=auth_headers).json()["method"] == "update_golden_note"
    assert client.delete("/contacts/contact-1/client-map/golden-notes/note-1", headers=auth_headers).status_code == 204
    assert client.get("/contacts/contact-1/client-map/meddpicc-score", headers=auth_headers).json()["method"] == "get_meddpicc_score"

    analyzed = client.post("/contacts/contact-1/client-map/analyze-behavior", headers=auth_headers)
    assert analyzed.json()["method"] == "analyze_behavior"


def test_tool_governance_routes_sign_internal_runtime_context(monkeypatch, auth_headers):
    fake = FakeToolGovernanceRouteClient()
    monkeypatch.setattr(tool_governance_routes, "tool_governance_client", fake)

    with TestClient(main.app) as test_client:
        listed = test_client.get("/tool-governance/policies", headers=auth_headers)
        updated = test_client.put(
            "/tool-governance/policies/mail-calendar.mail-read-search",
            json={"enabled": False, "team_scope": ["support"]},
            headers=auth_headers,
        )
        mine = test_client.get("/tool-governance/me", headers=auth_headers)
        preferences = test_client.put(
            "/tool-governance/me/preferences",
            json={"preferred_email_provider": "microsoft_outlook"},
            headers=auth_headers,
        )

    assert listed.status_code == 200
    assert updated.status_code == 200
    assert mine.status_code == 200
    assert preferences.status_code == 200
    assert [call[0] for call in fake.calls] == [
        "list_policies",
        "update_policy",
        "get_my_access",
        "update_my_preferences",
    ]

    headers = fake.calls[0][1]
    signer = InternalSessionContextSigner(
        "dev-internal-session-secret-not-for-production",
        kid="internal-session-dev",
    )
    context = signer.validate(headers["X-Session-Context"])
    assert context.tenant_id == "tenant-1"
    assert context.user_id == "user-1"
    assert "agent_control.manage" in context.permissions


def test_auth_dependency_accepts_and_rejects_tokens():
    token = jwt.encode({"sub": "user-1", "email": "user@example.com", "type": "access"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    credentials = type("Credentials", (), {"credentials": token})()
    assert get_current_user(credentials)["user_id"] == "user-1"

    invalid = type("Credentials", (), {"credentials": "not-a-token"})()
    with pytest.raises(Exception) as exc_info:
        get_current_user(invalid)
    assert getattr(exc_info.value, "status_code", None) == 401

    no_sub = jwt.encode({"email": "user@example.com", "type": "access"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    no_sub_credentials = type("Credentials", (), {"credentials": no_sub})()
    with pytest.raises(Exception) as missing_sub:
        get_current_user(no_sub_credentials)
    assert getattr(missing_sub.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_behavioral_analyzer_delegates_to_client_map_backend():
    class FakeBehaviorAnalysisClient:
        async def analyze_behavior(self, contact_id, forward_headers=None):
            assert contact_id == "contact-1"
            return {"behavioral_profile": {"disc_primary": "I"}}

    profile = await BehavioralAnalyzer(FakeBehaviorAnalysisClient()).analyze("contact-1", "tenant-1")
    assert profile["disc_primary"] == "I"


@pytest.mark.asyncio
async def test_backend_client_methods_cover_paths(monkeypatch):
    fake_service = FakeServiceClient()

    monkeypatch.setattr("app.infrastructure.clients.agent_client.create_agent_backend_client", lambda: fake_service)

    bcc = BccClient()
    client_map = ClientMapClient()
    training = TrainingClient()

    bcc_calls = [
        ("list_organizations", ()),
        ("create_organization", ({"name": "Org"},)),
        ("get_organization", ("org-1",)),
        ("update_organization", ("org-1", {"name": "Org"})),
        ("delete_organization", ("org-1",)),
        ("update_org_profile", ("org-1", {"summary": "A"})),
        ("list_departments", ("org-1",)),
        ("create_department", ("org-1", {"name": "Sales"})),
        ("delete_department", ("dept-1",)),
        ("list_teams", ("dept-1",)),
        ("create_team", ("dept-1", {"name": "Team"})),
        ("delete_team", ("team-1",)),
        ("list_roles", ()),
        ("create_role", ({"name": "Role"},)),
        ("get_role", ("role-1",)),
        ("update_role", ("role-1", {"name": "Role"})),
        ("delete_role", ("role-1",)),
        ("list_team_roles", ("team-1",)),
        ("list_industries", ()),
        ("create_industry", ({"name": "Industry"},)),
        ("get_industry", ("industry-1",)),
        ("update_industry", ("industry-1", {"name": "Industry"})),
        ("delete_industry", ("industry-1",)),
        ("list_careers", ()),
        ("create_career", ({"name": "Career"},)),
        ("delete_career", ("career-1",)),
        ("list_skill_templates", ()),
        ("create_skill_template", ({"name": "Skill"},)),
        ("delete_skill_template", ("template-1",)),
        ("list_task_templates", ()),
        ("create_task_template", ({"name": "Task"},)),
        ("delete_task_template", ("template-1",)),
        ("list_domains", ()),
        ("create_domain", ({"name": "Domain"},)),
        ("delete_domain", ("domain-1",)),
        ("list_intents", ()),
        ("get_intent", ("intent-1",)),
        ("create_intent", ({"name": "Intent"},)),
        ("delete_intent", ("intent-1",)),
        ("get_cognitive_map", ()),
        ("list_regulations", ("org-1",)),
        ("create_regulation", ("org-1", {"name": "Reg"})),
        ("delete_regulation", ("reg-1",)),
        ("link_org_industry", ("org-1", "industry-1")),
        ("unlink_org_industry", ("org-1", "industry-1")),
        ("add_skill", ("role-1", {"name": "Skill"})),
        ("update_skill", ("skill-1", {"name": "Skill"})),
        ("delete_skill", ("skill-1",)),
        ("add_task", ("role-1", {"name": "Task"})),
        ("update_task", ("task-1", {"name": "Task"})),
        ("delete_task", ("task-1",)),
        ("add_task_step", ("task-1", {"name": "Step"})),
        ("add_resource", ("skill-1", {"name": "Resource"})),
        ("add_milestone", ("role-1", {"name": "Milestone"})),
        ("create_profile_entry", ("contact", "contact-1", {"section": "summary"})),
        ("get_profile", ("contact", "contact-1")),
        ("get_profile_history", ("contact", "contact-1")),
        ("get_profile_section", ("contact", "contact-1", "summary")),
    ]
    for method, args in bcc_calls:
        assert await getattr(bcc, method)(*args) is not None

    assert await bcc.get_organization("missing-id") is None
    assert await bcc.get_role("missing-id") is None
    assert await bcc.get_industry("missing-id") is None
    assert await bcc.get_intent("missing-id") is None

    assert await client_map.get("missing-id") is None
    assert (await client_map.get("contact-1"))["path"].endswith("/client-map")
    assert (await client_map.upsert("contact-1", {"role": "buyer"}))["json"]["role"] == "buyer"
    assert (await client_map.create_golden_note("contact-1", {"note": "A"}))["json"]["note"] == "A"
    assert (await client_map.update_golden_note("contact-1", "note-1", {"note": "B"}))["json"]["note"] == "B"
    assert await client_map.delete_golden_note("contact-1", "note-1") is True
    assert (await client_map.get_meddpicc_score("contact-1"))["path"].endswith("/meddpicc-score")
    assert await client_map.get_meddpicc_score("missing-id") is None
    assert (await client_map.analyze_behavior("contact-1"))["path"].endswith("/analyze-behavior")

    assert (await training.create_session({"topic": "CRM"}))["json"]["topic"] == "CRM"
    assert (await training.update_slide("session-1", {"slide": 2}))["json"]["slide"] == 2
    assert (await training.get_notes("session-1"))["path"].endswith("/notes")
    assert (await training.create_note("session-1", {"note": "A"}))["json"]["note"] == "A"
    assert await training.delete_note("note-1") is True
    assert (await training.get_missing("session-1"))["path"].endswith("/missing")
    assert (await training.create_missing("session-1", {"item": "X"}))["json"]["item"] == "X"
    assert await training.delete_missing("item-1") is True


def test_agent_backend_client_requires_explicit_service_url(monkeypatch):
    monkeypatch.delenv("AGENT_BACKEND_API_URL", raising=False)

    with pytest.raises(RuntimeError, match="AGENT_BACKEND_API_URL is required"):
        create_agent_backend_client()

    monkeypatch.setenv("AGENT_BACKEND_API_URL", "http://agent-backend-api:9008/")

    client = create_agent_backend_client()

    assert str(client.base_url) == "http://agent-backend-api:9008"


def test_python_package_contract_loads_runtime_components():
    from agent_control_b4f_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (
        agent_control_routes,
        bcc_routes,
        client_map_routes,
        tool_governance_routes,
        training_routes,
    )
    assert contract.load_runtime_client_classes() == (
        BccClient,
        ClientMapClient,
        ToolGovernanceClient,
        TrainingClient,
    )
