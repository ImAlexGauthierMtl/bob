from types import SimpleNamespace

from fastapi.testclient import TestClient
from jose import jwt

import main
from app.infrastructure.clients import provider_proxy
from app.infrastructure.clients.email_client import (
    ConnectionClient,
    EmailCrudClient,
    EventCrudClient,
    IntegrationSettingsClient,
    MembraneCrudClient,
    SmartLabelClient,
)
from app.middleware import auth as auth_module
from app.middleware.auth import settings
from app.presentation.routes import (
    integration_overview_routes,
    integration_settings_routes,
    membrane_routes,
    ms365_routes,
    smart_label_routes,
    webhook_routes,
)
from communication_b4f_api import contract


USER = {
    "user_id": "user-1",
    "email": "user@example.com",
    "tenant_id": "tenant-1",
    "active_organization_id": "org-1",
}


def integration_setting(**overrides):
    data = {
        "id": "setting-1",
        "integration_key": "microsoft-outlook",
        "scope_mode": "per-user",
        "is_enabled": True,
        "display_name": "Outlook",
        "notes": None,
        "tenant_id": "tenant-1",
    }
    data.update(overrides)
    return data


class FakeBackendResponse:
    def __init__(self, payload=None, status_code=200, headers=None, content=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {"content-type": "application/json"}
        self.content = content if content is not None else (b"" if payload is None else __import__("json").dumps(payload).encode())

    def json(self):
        return self._payload


class FakeProviderBackendClient:
    def __init__(self):
        self.calls = []

    async def get(self, path, params=None, forward_headers=None):
        self.calls.append(("GET", path, params, None, forward_headers))
        if path.split("?", 1)[0].endswith("/connect-redirect"):
            return FakeBackendResponse(
                status_code=200,
                headers={"content-type": "text/html; charset=utf-8"},
                content=b"<html>connect</html>",
            )
        return FakeBackendResponse({"path": path, "params": params or {}})

    async def post(self, path, json=None, forward_headers=None):
        self.calls.append(("POST", path, None, json, forward_headers))
        return FakeBackendResponse({"path": path, "json": json, "status": "ok"}, status_code=201)

    async def put(self, path, json=None, forward_headers=None):
        self.calls.append(("PUT", path, None, json, forward_headers))
        return FakeBackendResponse({"path": path, "json": json})

    async def patch(self, path, json=None, forward_headers=None):
        self.calls.append(("PATCH", path, None, json, forward_headers))
        return FakeBackendResponse({"path": path, "json": json})

    async def delete(self, path, forward_headers=None):
        self.calls.append(("DELETE", path, None, None, forward_headers))
        return FakeBackendResponse(status_code=404 if "missing" in path else 204)


class FakeIntegrationSettingsClient:
    async def list(self, forward_headers=None):
        return [integration_setting()]

    async def upsert(self, data, forward_headers=None):
        return integration_setting(**data)

    async def update(self, integration_key, data, forward_headers=None):
        return integration_setting(integration_key=integration_key, **data)

    async def delete(self, integration_key, forward_headers=None):
        return integration_key != "missing"


class FakeSmartLabelClient:
    async def list(self, skip=0, limit=50, forward_headers=None):
        return {"items": [{"id": "label-1", "name": "Client", "color": "#00aa00"}], "total": 1, "skip": skip, "limit": limit}

    async def get(self, label_id, forward_headers=None):
        return None if label_id == "missing" else {"id": label_id, "name": "Client", "color": "#00aa00"}

    async def create(self, data, forward_headers=None):
        return {"id": "label-new", **data}

    async def update(self, label_id, data, forward_headers=None):
        return {"id": label_id, "name": "Client", **data}

    async def delete(self, label_id, forward_headers=None):
        return label_id != "missing"


class FakeConnectionClient:
    async def get_by_user(self, user_id, forward_headers=None):
        return {"id": "ms365-connection-1", "user_id": user_id}


class FakeMembraneCrudClient:
    async def get_connection_by_user(self, user_id, integration_key=None, forward_headers=None):
        if integration_key == "microsoft-outlook":
            return {"id": "membrane-connection-1", "user_id": user_id, "integration_key": integration_key}
        return None


class FakeEventBus:
    async def publish(self, event_name, payload, tenant_id, triggered_by):
        return ["execution-1", "execution-2"]


def auth_headers():
    token = jwt.encode({**USER, "sub": USER["user_id"], "type": "access"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


def install_fakes(monkeypatch):
    provider_client = FakeProviderBackendClient()

    async def fake_profile(user_id, forward_headers):
        return {"is_super_admin": True, "role": "admin"}

    monkeypatch.setattr(auth_module, "_fetch_user_profile", fake_profile)
    monkeypatch.setattr(provider_proxy, "_client", provider_client)
    monkeypatch.setattr(integration_settings_routes, "integration_settings_client", FakeIntegrationSettingsClient())
    monkeypatch.setattr(smart_label_routes, "smart_label_client", FakeSmartLabelClient())
    monkeypatch.setattr(
        integration_overview_routes,
        "overview_service",
        integration_overview_routes.IntegrationOverviewService(
            FakeIntegrationSettingsClient(),
            FakeConnectionClient(),
            FakeMembraneCrudClient(),
            FakeSmartLabelClient(),
        ),
    )
    monkeypatch.setattr(webhook_routes, "event_bus", FakeEventBus())
    monkeypatch.setattr(webhook_routes, "settings", SimpleNamespace(webhook_api_key="public-key"))
    return provider_client


def test_monitoring_endpoints(monkeypatch):
    install_fakes(monkeypatch)
    with TestClient(main.app) as client:
        for path in ["/health", "/readiness", "/liveness", "/startup", "/metrics"]:
            assert client.get(path).status_code == 200
        assert "dependencies" in client.get("/health").json()
        assert "cde_api_info" in client.get("/metrics").text


def test_integration_settings_and_smart_labels(monkeypatch):
    install_fakes(monkeypatch)
    headers = auth_headers()
    with TestClient(main.app) as client:
        assert client.get("/integration-settings", headers=headers).json()["items"][0]["integration_key"] == "microsoft-outlook"
        assert client.post("/integration-settings", json={"integration_key": "gmail"}, headers=headers).status_code == 201
        assert client.patch("/integration-settings/gmail", json={"scope_mode": "per-tenant"}, headers=headers).json()["scope_mode"] == "per-tenant"
        assert client.delete("/integration-settings/gmail", headers=headers).status_code == 204
        assert client.delete("/integration-settings/missing", headers=headers).status_code == 404

        assert client.post("/inbox/labels", json={"name": "Client"}, headers=headers).status_code == 201
        assert client.get("/inbox/labels", headers=headers).json()["total"] == 1
        assert client.get("/inbox/labels/label-1", headers=headers).json()["id"] == "label-1"
        assert client.get("/inbox/labels/missing", headers=headers).status_code == 404
        assert client.patch("/inbox/labels/label-1", json={"color": "#ff0000"}, headers=headers).json()["color"] == "#ff0000"
        assert client.delete("/inbox/labels/label-1", headers=headers).status_code == 204


def test_integration_overview_composes_settings_connections_and_labels(monkeypatch):
    install_fakes(monkeypatch)
    headers = auth_headers()
    with TestClient(main.app) as client:
        payload = client.get("/integrations/overview", headers=headers).json()

    assert payload["tenant_id"] == "tenant-1"
    assert payload["totals"] == {"configured": 1, "enabled": 1, "connected": 1, "smart_labels": 1}
    assert payload["integrations"][0]["integration_key"] == "microsoft-outlook"
    assert payload["integrations"][0]["connection_provider"] == "membrane"
    assert payload["smart_labels"][0]["id"] == "label-1"


def test_webhook_routes(monkeypatch):
    install_fakes(monkeypatch)
    headers = auth_headers()
    body = {"event": "contact.created", "data": {"id": "contact-1"}, "source": "test"}
    with TestClient(main.app) as client:
        assert client.post("/webhooks/trigger", json=body, headers=headers).json()["executions_triggered"] == 2
        assert client.post("/webhooks/trigger/public", json=body, headers={"X-API-Key": "public-key"}).json()["status"] == "accepted"
        assert client.post("/webhooks/trigger/public", json=body, headers={"X-API-Key": "bad"}).status_code == 401
        assert "contact.created" in client.get("/webhooks/events", headers=headers).json()


def test_provider_routes_are_proxied_to_email_backend(monkeypatch):
    provider_client = install_fakes(monkeypatch)
    headers = auth_headers()
    with TestClient(main.app) as client:
        response = client.get("/ms365/auth-url", params={"prompt": "select_account"}, headers=headers)
        assert response.json()["path"] == "/api/v1/provider/ms365/auth-url?prompt=select_account"

        response = client.post(
            "/ms365/emails/send",
            json={"subject": "Hello", "to_recipients": ["a@example.com"]},
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["path"] == "/api/v1/provider/ms365/emails/send"

        response = client.post("/membrane/token", json={"integration_key": "microsoft-outlook"}, headers=headers)
        assert response.json()["path"] == "/api/v1/provider/membrane/token"

        response = client.get(
            "/membrane/connect-redirect",
            params={"integration_key": "microsoft-outlook", "redirect_uri": "https://app.example.test", "token": "token"},
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        assert client.delete("/membrane/connections/missing", headers=headers).status_code == 404

    assert provider_client.calls[0][1] == "/api/v1/provider/ms365/auth-url?prompt=select_account"
    assert dict(provider_client.calls[0][4])["authorization"].startswith("Bearer ")


def test_b4f_provider_route_modules_are_thin_proxies():
    assert not hasattr(ms365_routes, "graph_service")
    assert not hasattr(ms365_routes, "MS365SyncService")
    assert not hasattr(membrane_routes, "MembraneClient")
    assert hasattr(ms365_routes, "proxy_ms365")
    assert hasattr(membrane_routes, "proxy_membrane")


def test_python_package_contract_loads_runtime_components():
    assert contract.load_app() is main.app
    assert len(contract.load_runtime_routes()) == 6
    assert contract.load_runtime_client_classes() == (
        IntegrationSettingsClient,
        ConnectionClient,
        EmailCrudClient,
        EventCrudClient,
        SmartLabelClient,
        MembraneCrudClient,
    )
