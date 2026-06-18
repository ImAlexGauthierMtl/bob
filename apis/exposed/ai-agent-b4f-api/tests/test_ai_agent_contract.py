from jose import jwt
import pytest
from fastapi.testclient import TestClient

import main
from app.application.services import capability_resolver
from app.application.services.capability_resolver import CapabilityResolver
from app.application.use_cases.behavioral_analyzer import BehavioralAnalyzer
from app.infrastructure.clients.agent_client import (
    BccClient,
    BobSettingsClient,
    CapabilityClient,
    ClientMapClient,
    TrainingClient,
)
from app.middleware.auth import get_current_user, settings
from app.presentation.routes import (
    bcc_routes,
    bob_chat_routes,
    bob_settings_routes,
    capability_routes,
    client_map_routes,
    training_routes,
)


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
            if name == "check":
                return {"granted": True, "capability_code": args[0]}
            if name == "get_user_capabilities":
                return {"user_id": args[0], "agent_mode": "auto", "capabilities": ["bob.chat"]}
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


class FakeResponse:
    def __init__(self, payload_data=None, status_code=200):
        self._payload = payload_data or {}
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class FakeServiceClient:
    def __init__(self, service_name):
        self.service_name = service_name
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
    bob_settings = FakeRouteClient()
    client_map = FakeRouteClient()
    capabilities = FakeRouteClient()
    training = FakeRouteClient()

    monkeypatch.setattr(bcc_routes, "bcc_client", bcc)
    monkeypatch.setattr(bob_settings_routes, "bob_settings_client", bob_settings)
    monkeypatch.setattr(client_map_routes, "client_map_client", client_map)
    monkeypatch.setattr(capability_routes, "capability_client", capabilities)
    monkeypatch.setattr(training_routes, "training_client", training)
    bob_chat_routes._sessions.clear()

    with TestClient(main.app) as test_client:
        yield test_client
    bob_chat_routes._sessions.clear()


@pytest.fixture()
def auth_headers():
    token = jwt.encode(
        {"sub": "user-1", "email": "user@example.com", "tenant_id": "tenant-1", "type": "access"},
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


def test_bob_settings_capabilities_training_and_client_map_routes(client, auth_headers, monkeypatch):
    assert client.get("/bob/settings", headers=auth_headers).json()["method"] == "get"
    assert client.put("/bob/settings", json={"tone": "direct"}, headers=auth_headers).json()["method"] == "update"
    assert client.delete("/bob/settings", headers=auth_headers).status_code == 204

    assert client.get("/capabilities/catalog", headers=auth_headers).json()["method"] == "list_catalog"
    assert client.get("/capabilities/users/user-2", headers=auth_headers).json()["user_id"] == "user-2"
    assert client.get("/capabilities/me", headers=auth_headers).json()["method"] == "get_my_capabilities"
    assert client.post("/capabilities/users/user-2/assign", json={"code": "bob.chat"}, headers=auth_headers).status_code == 201
    assert client.post("/capabilities/check", params={"capability_code": "bob.chat"}, headers=auth_headers).json()["granted"] is True

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

    async def fake_llm(self, signals):
        return {"disc_primary": "D", "disc_confidence": 0.9, "communication_tips": ["Be concise"]}

    monkeypatch.setattr(BehavioralAnalyzer, "_llm_analyze", fake_llm)
    analyzed = client.post("/contacts/contact-1/client-map/analyze-behavior", headers=auth_headers)
    assert analyzed.json()["behavioral_profile"]["disc_primary"] == "D"


def test_bob_chat_sessions_are_scoped_to_user_id(client, auth_headers):
    response = client.post("/bob/chat", json={"message": "Plan my next call"}, headers=auth_headers)
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    assert response.json()["turn_count"] == 1

    sessions = client.get("/bob/sessions", headers=auth_headers).json()
    assert sessions[0]["session_id"] == session_id
    assert sessions[0]["user_id"] == "user-1"

    assert client.delete(f"/bob/sessions/{session_id}", headers=auth_headers).status_code == 204
    assert client.get("/bob/sessions", headers=auth_headers).json() == []


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
async def test_capability_resolver_and_behavioral_analyzer(monkeypatch):
    class FakeCapabilityClient:
        async def check(self, capability_code, forward_headers=None):
            return {"granted": capability_code == "bob.chat"}

        async def get_user_capabilities(self, user_id, forward_headers=None):
            return {"user_id": user_id, "agent_mode": "auto", "capabilities": ["bob.chat"]}

    monkeypatch.setattr(capability_resolver, "capability_client", FakeCapabilityClient())
    resolver = CapabilityResolver()
    assert await resolver.can("user-1", "bob.chat") is True
    assert await resolver.can("user-1", "unknown") is False
    assert (await resolver.get_all_capabilities("user-1"))["agent_mode"] == "auto"
    assert resolver.get_agent_mode(0.7) == "auto"
    assert resolver.get_agent_mode(0.4) == "approval"
    assert resolver.get_agent_mode(0.1) == "suggest"

    async def fake_llm(self, signals):
        assert signals["golden_note_signals"]["total_notes"] == 1
        return {"disc_primary": "I", "communication_tips": ["Mirror enthusiasm"]}

    monkeypatch.setattr(BehavioralAnalyzer, "_llm_analyze", fake_llm)
    client_map = FakeBehaviorClientMap()
    profile = await BehavioralAnalyzer(client_map).analyze("contact-1", "tenant-1")
    assert profile["disc_primary"] == "I"
    assert client_map.updated[0][1]["behavioral_profile"]["disc_primary"] == "I"


@pytest.mark.asyncio
async def test_backend_client_methods_cover_paths(monkeypatch):
    services = {}

    def fake_factory(name):
        services.setdefault(name, FakeServiceClient(name))
        return services[name]

    monkeypatch.setattr("app.infrastructure.clients.agent_client.create_service_client", fake_factory)

    bcc = BccClient()
    bob_settings = BobSettingsClient()
    client_map = ClientMapClient()
    capabilities = CapabilityClient()
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

    assert (await bob_settings.get())["path"] == "/api/v1/bob/settings"
    assert (await bob_settings.update({"tone": "direct"}))["json"]["tone"] == "direct"
    assert await bob_settings.reset() is True

    assert await client_map.get("missing-id") is None
    assert (await client_map.get("contact-1"))["path"].endswith("/client-map")
    assert (await client_map.upsert("contact-1", {"role": "buyer"}))["json"]["role"] == "buyer"
    assert (await client_map.create_golden_note("contact-1", {"note": "A"}))["json"]["note"] == "A"
    assert (await client_map.update_golden_note("contact-1", "note-1", {"note": "B"}))["json"]["note"] == "B"
    assert await client_map.delete_golden_note("contact-1", "note-1") is True
    assert (await client_map.get_meddpicc_score("contact-1"))["path"].endswith("/meddpicc-score")
    assert await client_map.get_meddpicc_score("missing-id") is None

    assert (await capabilities.list_catalog())["path"] == "/api/v1/capabilities/catalog"
    assert (await capabilities.get_user_capabilities("user-1"))["path"].endswith("/user-1")
    assert (await capabilities.get_my_capabilities())["path"] == "/api/v1/capabilities/me"
    assert (await capabilities.assign("user-1", {"code": "bob.chat"}))["json"]["code"] == "bob.chat"
    assert (await capabilities.check("bob.chat"))["granted"] is True

    assert (await training.create_session({"topic": "CRM"}))["json"]["topic"] == "CRM"
    assert (await training.update_slide("session-1", {"slide": 2}))["json"]["slide"] == 2
    assert (await training.get_notes("session-1"))["path"].endswith("/notes")
    assert (await training.create_note("session-1", {"note": "A"}))["json"]["note"] == "A"
    assert await training.delete_note("note-1") is True
    assert (await training.get_missing("session-1"))["path"].endswith("/missing")
    assert (await training.create_missing("session-1", {"item": "X"}))["json"]["item"] == "X"
    assert await training.delete_missing("item-1") is True


def test_python_package_contract_loads_runtime_components():
    from ai_agent_b4f_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (
        bcc_routes,
        bob_settings_routes,
        bob_chat_routes,
        client_map_routes,
        capability_routes,
        training_routes,
    )
    assert contract.load_runtime_client_classes() == (
        BccClient,
        BobSettingsClient,
        ClientMapClient,
        CapabilityClient,
        TrainingClient,
    )
