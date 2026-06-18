from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.infrastructure.clients.platform_clients import UsageClient, WorkflowClient
from app.middleware.auth import get_current_user, settings
from app.presentation.routes import enrichment_routes, overview_routes, usage_routes, workflow_routes


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
