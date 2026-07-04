from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.infrastructure.clients import email_client as email_client_module
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
    pipedream_routes,
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


def connection(**overrides):
    data = {
        "id": "conn-1",
        "user_id": "user-1",
        "integration_key": "microsoft-outlook",
        "status": "connected",
    }
    data.update(overrides)
    return data


def smart_label(**overrides):
    data = {
        "id": "label-1",
        "name": "Client",
        "color": "#111111",
    }
    data.update(overrides)
    return data


def membrane_connection(**overrides):
    data = {
        "id": "membrane-1",
        "user_id": "user-1",
        "integration_key": "microsoft-outlook",
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

    async def delete_connection(self, connection_id, forward_headers=None):
        return connection_id != "missing"


class FakeResponse:
    def __init__(self, payload=None, status_code=200, text=""):
        self._payload = payload or {}
        self.status_code = status_code
        self.text = text or str(self._payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeEmailBackendServiceClient:
    def __init__(self):
        self.calls = []

    async def get(self, path, params=None, forward_headers=None):
        self.calls.append(("GET", path, params, forward_headers))
        if "missing" in path:
            return FakeResponse(status_code=404)
        if path == "/api/v1/integration-settings":
            return FakeResponse({"items": [integration_setting()]})
        if path.endswith("/active/all"):
            return FakeResponse([connection()])
        if "/membrane/connections/by-user/" in path:
            return FakeResponse(membrane_connection())
        if "/membrane/connections/" in path:
            return FakeResponse(membrane_connection(id=path.rsplit("/", 1)[-1]))
        if "/connections/by-user/" in path:
            return FakeResponse(connection())
        if "/connections/" in path:
            return FakeResponse(connection(id=path.rsplit("/", 1)[-1]))
        if path == "/api/v1/membrane/emails":
            return FakeResponse({"items": [{"id": "membrane-email-1"}], "total": 1})
        if "/membrane/emails/" in path:
            return FakeResponse({"id": path.rsplit("/", 1)[-1]})
        if path == "/api/v1/membrane/events":
            return FakeResponse({"items": [{"id": "membrane-event-1"}], "total": 1})
        if "/membrane/events/" in path:
            return FakeResponse({"id": path.rsplit("/", 1)[-1]})
        if path == "/api/v1/emails":
            return FakeResponse({"items": [{"id": "email-1"}], "total": 1})
        if "/emails/" in path:
            return FakeResponse({"id": path.rsplit("/", 1)[-1]})
        if path == "/api/v1/events":
            return FakeResponse({"items": [{"id": "event-1"}], "total": 1})
        if "/events/" in path:
            return FakeResponse({"id": path.rsplit("/", 1)[-1]})
        if path == "/api/v1/smart-labels":
            return FakeResponse({"items": [smart_label()], "total": 1})
        if "/smart-labels/" in path:
            return FakeResponse(smart_label(id=path.rsplit("/", 1)[-1]))
        return FakeResponse({"ok": True})

    async def post(self, path, json=None, forward_headers=None):
        self.calls.append(("POST", path, json, forward_headers))
        return FakeResponse({"id": "created", **(json or {})})

    async def patch(self, path, json=None, params=None, forward_headers=None):
        self.calls.append(("PATCH", path, json, params, forward_headers))
        return FakeResponse({"id": path.rsplit("/", 1)[-1], **(json or {})})

    async def delete(self, path, params=None, forward_headers=None):
        self.calls.append(("DELETE", path, params, forward_headers))
        return FakeResponse(status_code=404 if "missing" in path else 204)


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
    monkeypatch.setattr(pipedream_routes, "membrane_crud_client", FakeMembraneCrudClient())
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
        response = client.post("/webhooks/trigger", json=body, headers=headers).json()
        assert response["status"] == "accepted"
        assert response["executions_triggered"] == 0
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

        response = client.post("/pipedream/token", json={"integration_key": "microsoft-outlook"}, headers=headers)
        assert response.json()["path"] == "/api/v1/provider/pipedream/token"

        response = client.get(
            "/pipedream/connect-url",
            params={"integration_key": "microsoft-outlook", "redirect_uri": "https://app.example.test"},
        )
        assert response.status_code in {200, 401, 503}

        response = client.get("/pipedream/integrations/github/tools", params={"limit": 5}, headers=headers)
        assert response.json()["path"] == "/api/v1/provider/pipedream/integrations/github/tools?limit=5"

        assert client.delete("/pipedream/connections/missing", headers=headers).status_code in {204, 404, 503}
        assert client.delete("/pipedream/local-connections/membrane-connection-1", headers=headers).status_code == 204
        assert client.delete("/pipedream/local-connections/missing", headers=headers).status_code == 404

    assert provider_client.calls[0][1] == "/api/v1/provider/ms365/auth-url?prompt=select_account"
    assert dict(provider_client.calls[0][4])["authorization"].startswith("Bearer ")


def test_b4f_provider_route_modules_are_thin_proxies():
    assert not hasattr(ms365_routes, "graph_service")
    assert not hasattr(ms365_routes, "MS365SyncService")
    assert not hasattr(pipedream_routes, "PipedreamClient")
    assert hasattr(ms365_routes, "proxy_ms365")
    assert hasattr(pipedream_routes, "proxy_pipedream")


@pytest.mark.asyncio
async def test_email_backend_clients_cover_crud_paths(monkeypatch):
    service_client = FakeEmailBackendServiceClient()
    monkeypatch.setattr(email_client_module, "create_service_client", lambda name: service_client)

    integration = IntegrationSettingsClient()
    assert (await integration.list())[0]["integration_key"] == "microsoft-outlook"
    assert (await integration.get("microsoft-outlook"))["id"] == "setting-1"
    assert await integration.get("missing") is None
    assert (await integration.upsert({"integration_key": "gmail"}))["integration_key"] == "gmail"
    assert (await integration.update("gmail", {"enabled": True}))["enabled"] is True
    assert await integration.delete("gmail") is True

    connections = ConnectionClient()
    assert (await connections.get_by_user("user-1"))["id"] == "conn-1"
    assert (await connections.get("conn-1"))["id"] == "conn-1"
    assert await connections.get("missing") is None
    assert (await connections.list_active())[0]["id"] == "conn-1"
    assert (await connections.create({"user_id": "user-1"}))["user_id"] == "user-1"
    assert (await connections.update("conn-1", {"status": "connected"}))["status"] == "connected"
    assert await connections.delete("conn-1") is True

    emails = EmailCrudClient()
    assert (await emails.list("user-1", folder="inbox", search="hello", smart_label="client", linked_contact_id="contact-1"))["total"] == 1
    assert (await emails.get("email-1", "user-1"))["id"] == "email-1"
    assert await emails.get("missing", "user-1") is None
    assert (await emails.upsert({"subject": "Hi"}))["subject"] == "Hi"
    assert (await emails.update("email-1", {"is_read": True}, "user-1"))["is_read"] is True
    assert await emails.delete("email-1", "user-1") is True

    events = EventCrudClient()
    assert (await events.list("user-1", from_date="2026-01-01", to_date="2026-01-02"))["total"] == 1
    assert (await events.get("event-1", "user-1"))["id"] == "event-1"
    assert await events.get("missing", "user-1") is None
    assert (await events.upsert({"title": "Meet"}))["title"] == "Meet"
    assert (await events.update("event-1", {"status": "confirmed"}, "user-1"))["status"] == "confirmed"
    assert await events.delete("event-1", "user-1") is True

    labels = SmartLabelClient()
    assert (await labels.list())["total"] == 1
    assert (await labels.get("label-1"))["id"] == "label-1"
    assert await labels.get("missing") is None
    assert (await labels.create({"name": "VIP"}))["name"] == "VIP"
    assert (await labels.update("label-1", {"color": "#fff"}))["color"] == "#fff"
    assert await labels.delete("label-1") is True

    membrane = MembraneCrudClient()
    assert (await membrane.upsert_connection({"id": "membrane-1"}))["id"] == "membrane-1"
    assert (await membrane.get_connection("membrane-1"))["id"] == "membrane-1"
    assert await membrane.get_connection("missing") is None
    assert (await membrane.upsert_email({"id": "membrane-email-1"}))["id"] == "membrane-email-1"
    assert (await membrane.upsert_event({"id": "membrane-event-1"}))["id"] == "membrane-event-1"
    assert (await membrane.get_connection_by_user("user-1", integration_key="microsoft-outlook"))["id"] == "membrane-1"
    assert await membrane.delete_connection("membrane-connection-1") is True
    assert (await membrane.list_emails("user-1", folder="inbox", search="q"))["total"] == 1
    assert (await membrane.get_email("email-1", "user-1"))["id"] == "email-1"
    assert await membrane.get_email("missing", "user-1") is None
    assert (await membrane.get_event("event-1", "user-1"))["id"] == "event-1"
    assert await membrane.get_event("missing", "user-1") is None
    assert (await membrane.list_events("user-1", from_date="2026-01-01", to_date="2026-01-02"))["total"] == 1


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
