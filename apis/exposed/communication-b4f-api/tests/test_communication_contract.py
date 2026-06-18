from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.infrastructure.clients.email_client import (
    ConnectionClient,
    EmailCrudClient,
    EventCrudClient,
    IntegrationSettingsClient,
    MembraneCrudClient,
    SmartLabelClient,
)
from app.middleware import auth as auth_module
from app.middleware.auth import get_current_user, settings
from app.presentation.routes import (
    integration_settings_routes,
    membrane_email_routes,
    membrane_routes,
    ms365_routes,
    smart_label_routes,
    webhook_routes,
)
from app.application.services import membrane_sync_service, ms365_sync_service
from app.infrastructure.external import membrane_service, ms365_graph_service


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


def email_payload(**overrides):
    data = {
        "id": "email-1",
        "user_id": "user-1",
        "ms_message_id": "ms-1",
        "provider_message_id": "provider-1",
        "membrane_connection_id": "local-conn-1",
        "subject": "Hello",
        "from_address": "sender@example.com",
        "from_name": "Sender",
        "to_addresses": [{"address": "user@example.com", "name": "User"}],
        "body_preview": "Preview",
        "body_html": "<p>Hello</p>",
        "is_read": False,
        "has_attachments": False,
        "folder": "inbox",
        "conversation_id": "conv-1",
    }
    data.update(overrides)
    return data


def event_payload(**overrides):
    data = {
        "id": "event-1",
        "user_id": "user-1",
        "ms_event_id": "ms-event-1",
        "subject": "Meeting",
        "start_time": "2026-01-01T10:00:00+00:00",
        "end_time": "2026-01-01T11:00:00+00:00",
        "is_all_day": False,
        "is_cancelled": False,
    }
    data.update(overrides)
    return data


def connection_payload(**overrides):
    data = {
        "id": "conn-1",
        "user_id": "user-1",
        "ms_user_id": "ms-user-1",
        "ms_email": "user@example.com",
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "token_expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "is_active": True,
        "connection_status": "connected",
    }
    data.update(overrides)
    return data


class FakeResponse:
    def __init__(self, payload=None, status_code=200, text=""):
        self._payload = payload if payload is not None else {}
        self.status_code = status_code
        self.text = text or str(self._payload)
        self.content = b"" if payload is None else b"{}"

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"unexpected status {self.status_code}")


class FakeServiceClient:
    def __init__(self, service_name="email~backend-api"):
        self.service_name = service_name
        self.calls = []

    async def get(self, path, params=None, forward_headers=None):
        self.calls.append(("get", path, params, forward_headers))
        if "missing" in path:
            return FakeResponse(status_code=404)
        if "boom" in path:
            return FakeResponse(status_code=500, text="backend failed")
        if "/integration-settings" in path:
            return FakeResponse({"items": [integration_setting()]})
        if "/membrane/connections/by-user" in path:
            return FakeResponse({"id": "local-conn-1", "membrane_connection_id": "remote-conn-1", "integration_key": "microsoft-outlook"})
        if "/membrane/connections/" in path:
            return FakeResponse({"id": path.rsplit("/", 1)[-1], "membrane_connection_id": "remote-conn-1", "integration_key": "microsoft-outlook"})
        if "/membrane/emails/" in path:
            return FakeResponse(email_payload(id=path.rsplit("/", 1)[-1]))
        if "/membrane/events/" in path:
            return FakeResponse(event_payload(id=path.rsplit("/", 1)[-1]))
        if "/membrane/emails" in path:
            return FakeResponse({"items": [email_payload()], "total": 1, "skip": int(params.get("skip", 0)), "limit": int(params.get("limit", 50))})
        if "/membrane/events" in path:
            return FakeResponse({"items": [event_payload()], "total": 1, "skip": int(params.get("skip", 0)), "limit": int(params.get("limit", 50))})
        if "/connections/by-user" in path:
            return FakeResponse(connection_payload())
        if "/connections/active/all" in path:
            return FakeResponse([connection_payload()])
        if "/connections/" in path:
            return FakeResponse(connection_payload(id=path.rsplit("/", 1)[-1]))
        if "/smart-labels" in path:
            if path.rstrip("/").endswith("smart-labels"):
                return FakeResponse({"items": [{"id": "label-1", "name": "Client"}], "total": 1, "skip": 0, "limit": 50})
            return FakeResponse({"id": path.rsplit("/", 1)[-1], "name": "Client"})
        if "/emails/" in path:
            return FakeResponse(email_payload(id=path.rsplit("/", 1)[-1]))
        if "/emails" in path:
            return FakeResponse({"items": [email_payload()], "total": 1, "skip": int(params.get("skip", 0)), "limit": int(params.get("limit", 50))})
        if "/events/" in path:
            return FakeResponse(event_payload(id=path.rsplit("/", 1)[-1]))
        if "/events" in path:
            return FakeResponse({"items": [event_payload()], "total": 1, "skip": int(params.get("skip", 0)), "limit": int(params.get("limit", 50))})
        return FakeResponse({"path": path, "params": params})

    async def post(self, path, json=None, forward_headers=None):
        self.calls.append(("post", path, json, forward_headers))
        if "/integration-settings" in path:
            return FakeResponse(integration_setting(**(json or {})), status_code=201)
        if "/connections" in path:
            return FakeResponse(connection_payload(**(json or {})), status_code=201)
        if "/smart-labels" in path:
            return FakeResponse({"id": "label-new", **(json or {})}, status_code=201)
        if "/membrane/connections" in path:
            return FakeResponse({"id": "local-conn-1", **(json or {})}, status_code=201)
        if "/membrane/emails" in path:
            return FakeResponse({"id": "email-new", **(json or {})}, status_code=201)
        if "/membrane/events" in path:
            return FakeResponse({"id": "event-new", **(json or {})}, status_code=201)
        if "/emails" in path:
            return FakeResponse({"id": "email-new", **(json or {})}, status_code=201)
        if "/events" in path:
            return FakeResponse({"id": "event-new", **(json or {})}, status_code=201)
        return FakeResponse({"path": path, "json": json}, status_code=201)

    async def patch(self, path, json=None, params=None, forward_headers=None):
        self.calls.append(("patch", path, json, forward_headers))
        if "/integration-settings" in path:
            return FakeResponse(integration_setting(integration_key=path.rsplit("/", 1)[-1], **(json or {})))
        if "/connections/" in path:
            return FakeResponse(connection_payload(id=path.rsplit("/", 1)[-1], **(json or {})))
        if "/smart-labels/" in path:
            return FakeResponse({"id": path.rsplit("/", 1)[-1], "name": "Client", **(json or {})})
        if "/emails/" in path:
            return FakeResponse(email_payload(id=path.rsplit("/", 1)[-1], **(json or {})))
        if "/events/" in path:
            return FakeResponse(event_payload(id=path.rsplit("/", 1)[-1], **(json or {})))
        return FakeResponse({"path": path, "json": json, "params": params})

    async def delete(self, path, params=None, forward_headers=None):
        self.calls.append(("delete", path, params, forward_headers))
        return FakeResponse(status_code=404 if "missing" in path else 204)


class FakeIntegrationSettingsClient:
    async def list(self, forward_headers=None):
        return [integration_setting()]

    async def upsert(self, data, forward_headers=None):
        return integration_setting(**data)

    async def get(self, integration_key, forward_headers=None):
        if integration_key == "hubspot":
            return integration_setting(integration_key=integration_key, scope_mode="per-organization")
        return integration_setting(integration_key=integration_key or "microsoft-outlook")

    async def update(self, integration_key, data, forward_headers=None):
        return integration_setting(integration_key=integration_key, **data)

    async def delete(self, integration_key, forward_headers=None):
        return integration_key != "missing"


class FakeSmartLabelClient:
    async def list(self, skip=0, limit=50, forward_headers=None):
        return {"items": [{"id": "label-1", "name": "Client", "color": "#00aa00"}], "total": 1, "skip": skip, "limit": limit}

    async def get(self, label_id, forward_headers=None):
        if label_id == "missing":
            return None
        return {"id": label_id, "name": "Client", "color": "#00aa00"}

    async def create(self, data, forward_headers=None):
        return {"id": "label-new", **data}

    async def update(self, label_id, data, forward_headers=None):
        return {"id": label_id, "name": "Client", **data}

    async def delete(self, label_id, forward_headers=None):
        return label_id != "missing"


class FakeConnectionClient:
    async def get_by_user(self, user_id, forward_headers=None):
        if user_id == "missing":
            return None
        return connection_payload(user_id=user_id)

    async def get(self, conn_id, forward_headers=None):
        return connection_payload(id=conn_id)

    async def list_active(self, forward_headers=None):
        return [connection_payload()]

    async def create(self, data, forward_headers=None):
        return connection_payload(**data)

    async def update(self, conn_id, data, forward_headers=None):
        return connection_payload(id=conn_id, **data)

    async def delete(self, conn_id, forward_headers=None):
        return conn_id != "missing"


class FakeEmailCrudClient:
    async def list(self, user_id, skip=0, limit=50, folder=None, search=None, smart_label=None, linked_contact_id=None, forward_headers=None):
        return {"items": [email_payload(user_id=user_id)], "total": 1, "skip": skip, "limit": limit}

    async def get(self, email_id, user_id, forward_headers=None):
        if email_id == "missing":
            return None
        return email_payload(id=email_id, user_id=user_id)

    async def upsert(self, data, forward_headers=None):
        return {"id": "email-new", **data}

    async def update(self, email_id, data, user_id, forward_headers=None):
        return email_payload(id=email_id, user_id=user_id, **data)

    async def delete(self, email_id, user_id, forward_headers=None):
        return email_id != "missing"


class FakeEventCrudClient:
    async def list(self, user_id, skip=0, limit=50, from_date=None, to_date=None, forward_headers=None):
        return {"items": [event_payload(user_id=user_id)], "total": 1, "skip": skip, "limit": limit}

    async def get(self, event_id, user_id, forward_headers=None):
        if event_id == "missing":
            return None
        return event_payload(id=event_id, user_id=user_id)

    async def upsert(self, data, forward_headers=None):
        return {"id": "event-new", **data}

    async def update(self, event_id, data, user_id, forward_headers=None):
        return event_payload(id=event_id, user_id=user_id, **data)

    async def delete(self, event_id, user_id, forward_headers=None):
        return event_id != "missing"


class FakeMembraneCrudClient:
    def __init__(self):
        self.upserted_emails = []

    async def upsert_connection(self, data, forward_headers=None):
        return {"id": "local-conn-1", **data}

    async def get_connection(self, connection_id, forward_headers=None):
        if connection_id == "missing":
            return None
        return {"id": connection_id, "membrane_connection_id": "remote-conn-1", "integration_key": "microsoft-outlook"}

    async def upsert_email(self, data, forward_headers=None):
        self.upserted_emails.append(data)
        return {"id": "email-upserted", **data}

    async def upsert_event(self, data, forward_headers=None):
        return {"id": "event-upserted", **data}

    async def get_connection_by_user(self, user_id, integration_key=None, forward_headers=None):
        if user_id == "missing":
            return None
        return {
            "id": "local-conn-1",
            "user_id": user_id,
            "membrane_connection_id": "remote-conn-1",
            "integration_key": integration_key or "microsoft-outlook",
        }

    async def list_emails(self, user_id, skip=0, limit=50, folder=None, search=None, forward_headers=None):
        return {"items": [email_payload(user_id=user_id)], "total": 1, "skip": skip, "limit": limit}

    async def get_email(self, email_id, user_id, forward_headers=None):
        if email_id == "missing":
            return None
        return email_payload(id=email_id, user_id=user_id)

    async def get_event(self, event_id, user_id, forward_headers=None):
        if event_id == "missing":
            return None
        return event_payload(id=event_id, user_id=user_id)

    async def list_events(self, user_id, skip=0, limit=50, from_date=None, to_date=None, forward_headers=None):
        return {"items": [event_payload(user_id=user_id)], "total": 1, "skip": skip, "limit": limit}


class NoConnectionMembraneCrudClient(FakeMembraneCrudClient):
    async def get_connection_by_user(self, user_id, integration_key=None, forward_headers=None):
        return None


class FakeEventBus:
    async def publish(self, event_name, payload, tenant_id, triggered_by):
        return ["execution-1", "execution-2"]


class FakeGraphService:
    _client_id = "client-id"
    _client_secret = "client-secret"
    _redirect_uri = "http://localhost/callback"

    def build_auth_url(self, state=None):
        return f"https://login.example.test/auth?state={state}"

    async def exchange_code_for_tokens(self, code):
        return {"access_token": "access-token", "refresh_token": "refresh-token", "expires_in": 3600, "scope": "Mail.Read"}

    async def get_user_profile(self, access_token):
        return {"id": "ms-user-1", "mail": "user@example.com"}

    async def ensure_valid_token(self, access_token, refresh_token, expires_at):
        return "valid-token", {"access_token": "valid-token"} if access_token == "expired" else None

    async def send_mail(self, **kwargs):
        return {"status": "sent", "subject": kwargs["subject"]}

    async def reply_mail(self, **kwargs):
        return {"status": "sent", "reply_all": kwargs["reply_all"]}

    async def forward_mail(self, **kwargs):
        return {"status": "sent", "to": kwargs["to_recipients"]}


class FakeMS365SyncService:
    def __init__(self, forward_headers=None):
        self.forward_headers = forward_headers

    async def sync_emails(self, connection):
        return 1

    async def sync_calendar(self, connection):
        return 1

    async def handle_webhook_notification(self, notifications):
        return None


class FakeLLMClient:
    def chat(self, **kwargs):
        return '{"summary": "Short summary", "smart_label": "Client", "action_items": ["Reply"]}'


class FakeMembraneClient:
    def __init__(self, token=None):
        self.token = token
        self.closed = False

    async def list_connections(self):
        return [
            {
                "id": "remote-conn-1",
                "integrationId": "integration-1",
                "integrationKey": "microsoft-outlook",
                "connectorId": "connector-1",
                "key": "microsoft-outlook",
                "name": "Outlook",
                "connected": True,
                "disconnected": False,
                "state": "connected",
                "createdAt": "2026-01-01T00:00:00Z",
            }
        ]

    async def list_integrations(self):
        return [{"key": "~connector.microsoft-outlook", "name": "Outlook", "description": "Email", "logoUri": "logo.svg"}]

    async def delete_connection(self, connection_id):
        return connection_id != "missing"

    async def run_action(self, action_key, input_data, connection_id=None):
        return {"action_key": action_key, "input": input_data, "connection_id": connection_id}

    async def proxy_get(self, connection_id, path, params=None):
        return {"value": [{"id": "provider-email-1", "subject": "Hello"}], "connection_id": connection_id, "path": path, "params": params}

    async def proxy_post(self, connection_id, path, json_body):
        return {"connection_id": connection_id, "path": path, "json": json_body}

    async def close(self):
        self.closed = True


def close_background_task(coro):
    if hasattr(coro, "close"):
        coro.close()
    return SimpleNamespace(done=lambda: True)


@pytest.fixture()
def route_fakes(monkeypatch):
    fakes = SimpleNamespace(
        integration=FakeIntegrationSettingsClient(),
        labels=FakeSmartLabelClient(),
        connections=FakeConnectionClient(),
        emails=FakeEmailCrudClient(),
        events=FakeEventCrudClient(),
        membrane=FakeMembraneCrudClient(),
    )

    async def fake_profile(user_id, forward_headers):
        return {"is_super_admin": True, "role": "admin"}

    monkeypatch.setattr(auth_module, "_fetch_user_profile", fake_profile)
    monkeypatch.setattr(integration_settings_routes, "integration_settings_client", fakes.integration)
    monkeypatch.setattr(smart_label_routes, "smart_label_client", fakes.labels)
    monkeypatch.setattr(webhook_routes, "event_bus", FakeEventBus())
    monkeypatch.setattr(webhook_routes, "settings", SimpleNamespace(webhook_api_key="public-key"))
    monkeypatch.setattr(ms365_routes, "connection_client", fakes.connections)
    monkeypatch.setattr(ms365_routes, "email_crud_client", fakes.emails)
    monkeypatch.setattr(ms365_routes, "event_crud_client", fakes.events)
    monkeypatch.setattr(ms365_routes, "graph_service", FakeGraphService())
    monkeypatch.setattr(ms365_routes, "MS365SyncService", FakeMS365SyncService)
    monkeypatch.setattr(ms365_routes, "llm_client", FakeLLMClient())
    monkeypatch.setattr(ms365_routes.asyncio, "create_task", close_background_task)
    monkeypatch.setattr(ms365_routes.asyncio, "ensure_future", close_background_task)
    monkeypatch.setattr(membrane_routes, "integration_settings_client", fakes.integration)
    monkeypatch.setattr(membrane_routes, "generate_membrane_token", lambda **kwargs: "membrane-token")
    monkeypatch.setattr(membrane_routes, "MembraneClient", FakeMembraneClient)
    monkeypatch.setattr(
        membrane_routes,
        "settings",
        SimpleNamespace(membrane_api_url="https://api.getmembrane.test", membrane_webhook_secret=None),
    )
    monkeypatch.setattr("app.infrastructure.clients.email_client.membrane_crud_client", fakes.membrane)

    async def fake_sync_membrane_emails(user, local_connection, top=50, forward_headers=None):
        return {"synced": 1, "fetched": 1, "errors": []}

    monkeypatch.setattr("app.application.services.membrane_sync_service.sync_membrane_emails", fake_sync_membrane_emails)
    return fakes


@pytest.fixture()
def client(route_fakes):
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers():
    token = jwt.encode({**USER, "sub": USER["user_id"], "type": "access"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


def test_monitoring_endpoints(client):
    for path in ["/health", "/readiness", "/liveness", "/startup", "/metrics"]:
        response = client.get(path)
        assert response.status_code == 200
    assert "dependencies" in client.get("/health").json()
    assert "cde_api_info" in client.get("/metrics").text


def test_integration_settings_and_smart_labels(client, auth_headers):
    assert client.get("/integration-settings", headers=auth_headers).json()["items"][0]["integration_key"] == "microsoft-outlook"
    assert client.post("/integration-settings", json={"integration_key": "gmail"}, headers=auth_headers).status_code == 201
    assert client.patch("/integration-settings/gmail", json={"scope_mode": "per-tenant"}, headers=auth_headers).json()["scope_mode"] == "per-tenant"
    assert client.delete("/integration-settings/gmail", headers=auth_headers).status_code == 204
    assert client.delete("/integration-settings/missing", headers=auth_headers).status_code == 404

    assert client.post("/inbox/labels", json={"name": "Client"}, headers=auth_headers).status_code == 201
    assert client.get("/inbox/labels", headers=auth_headers).json()["total"] == 1
    assert client.get("/inbox/labels/label-1", headers=auth_headers).json()["id"] == "label-1"
    assert client.get("/inbox/labels/missing", headers=auth_headers).status_code == 404
    assert client.patch("/inbox/labels/label-1", json={"color": "#ff0000"}, headers=auth_headers).json()["color"] == "#ff0000"
    assert client.delete("/inbox/labels/label-1", headers=auth_headers).status_code == 204
    assert client.delete("/inbox/labels/missing", headers=auth_headers).status_code == 404


def test_webhook_routes(client, auth_headers):
    body = {"event": "contact.created", "data": {"id": "contact-1"}, "source": "test"}
    assert client.post("/webhooks/trigger", json=body, headers=auth_headers).json()["executions_triggered"] == 2
    assert client.post("/webhooks/trigger/public", json=body, headers={"X-API-Key": "public-key"}).json()["status"] == "accepted"
    assert client.post("/webhooks/trigger/public", json=body, headers={"X-API-Key": "bad"}).status_code == 401
    assert "contact.created" in client.get("/webhooks/events", headers=auth_headers).json()


def test_ms365_routes(client, auth_headers):
    assert client.get("/ms365/auth-url", headers=auth_headers).json()["auth_url"].endswith("state=user-1")
    assert client.get("/ms365/connection", headers=auth_headers).json()["user_id"] == "user-1"
    assert client.delete("/ms365/connection", headers=auth_headers).status_code == 204
    assert client.post("/ms365/sync", headers=auth_headers).json()["status"] == "started"
    assert client.get("/ms365/emails", headers=auth_headers).json()["total"] == 1
    assert client.get("/ms365/emails/email-1", headers=auth_headers).json()["id"] == "email-1"
    assert client.get("/ms365/emails/missing", headers=auth_headers).status_code == 404
    assert client.post("/ms365/emails/email-1/ai-insights", headers=auth_headers).json()["smart_label"] == "Client"
    assert client.post(
        "/ms365/emails/send",
        json={"subject": "Hello", "body_content": "Body", "to_recipients": ["a@example.com"]},
        headers=auth_headers,
    ).json()["status"] == "sent"
    assert client.post("/ms365/emails/email-1/reply", json={"comment": "Thanks"}, headers=auth_headers).json()["status"] == "sent"
    assert client.post(
        "/ms365/emails/email-1/forward",
        json={"to_recipients": ["b@example.com"], "comment": "FYI"},
        headers=auth_headers,
    ).json()["status"] == "sent"
    assert client.get("/ms365/events", headers=auth_headers).json()["total"] == 1
    assert client.get("/ms365/events/event-1", headers=auth_headers).json()["id"] == "event-1"
    assert client.get("/ms365/events/missing", headers=auth_headers).status_code == 404
    assert client.post("/ms365/webhook?validationToken=abc").text == "abc"
    assert client.post("/ms365/webhook", json={"value": []}).json()["status"] == "ok"
    callback = client.get("/ms365/callback", params={"code": "code-1", "state": "user-1"}, follow_redirects=False)
    assert callback.status_code in {302, 307}
    assert "ms365=connected" in callback.headers["location"]
    assert client.get("/ms365/callback", params={"code": "code-1"}).status_code == 400


def test_membrane_routes(client, auth_headers, route_fakes):
    assert client.post("/membrane/token", json={"integration_key": "microsoft-outlook"}, headers=auth_headers).json()["token"] == "membrane-token"
    assert client.get("/membrane/connections", params={"integration_key": "microsoft-outlook"}, headers=auth_headers).json()["items"][0]["id"] == "remote-conn-1"
    assert client.delete("/membrane/connections/remote-conn-1", headers=auth_headers).status_code == 204
    assert client.delete("/membrane/connections/missing", headers=auth_headers).status_code == 404
    assert client.get("/membrane/integrations", headers=auth_headers).json()["items"][0]["key"] == "microsoft-outlook"
    assert client.post("/membrane/actions/send-email/run", json={"connection_id": "remote-conn-1", "input": {"subject": "Hi"}}, headers=auth_headers).json()["success"] is True
    connect_url = client.get("/membrane/connect-url", params={"integration_key": "microsoft-outlook"}, headers=auth_headers).json()["url"]
    assert "/api/v1/membrane/connect-redirect" in connect_url
    redirect = client.get(
        "/membrane/connect-redirect",
        params={"integration_key": "microsoft-outlook", "redirect_uri": "https://app.example.test", "token": "token"},
    )
    assert redirect.status_code == 200
    assert "connectorKey" in redirect.text

    webhook_body = {
        "event_type": "unknown-event",
        "connection_id": "remote-conn-1",
        "integration_key": "microsoft-outlook",
        "tenant_key": "t:tenant-1:u:user-1",
        "data": {},
    }
    assert client.post("/membrane/webhook", json=webhook_body).json()["status"] == "ok"
    email_webhook = {
        **webhook_body,
        "event_type": "email-received",
        "data": {
            "connectionId": "remote-conn-1",
            "messageId": "provider-email-1",
            "subject": "Webhook email",
            "body": "<p>Hello from webhook</p>",
            "from": {"email": "sender@example.com", "name": "Sender"},
            "to": [{"email": "user@example.com", "name": "User"}],
            "cc": [{"email": "copy@example.com", "name": "Copy"}],
            "receivedAt": "2026-01-01T00:00:00Z",
            "isRead": False,
            "hasAttachments": True,
            "conversationId": "conv-webhook",
        },
    }
    assert client.post("/membrane/webhook", json=email_webhook).json()["status"] == "ok"
    event_webhook = {
        **webhook_body,
        "event_type": "event-created",
        "data": {
            "connection_id": "remote-conn-1",
            "eventId": "provider-event-1",
            "subject": "Webhook event",
            "body": "<p>Meeting</p>",
            "location": "Office",
            "startTime": "2026-01-01T10:00:00Z",
            "endTime": "2026-01-01T11:00:00Z",
            "organizer": {"email": "boss@example.com", "name": "Boss"},
            "attendees": [{"email": "user@example.com", "name": "User", "status": "accepted"}],
        },
    }
    assert client.post("/membrane/webhook", json=event_webhook).json()["status"] == "ok"
    assert client.post("/membrane/webhook", content=b"{bad-json").status_code == 400
    membrane_routes.settings.membrane_webhook_secret = "secret"
    assert client.post("/membrane/webhook", json=webhook_body).status_code == 401
    membrane_routes.settings.membrane_webhook_secret = None
    assert client.get("/membrane/connections/by-user/user-1", headers=auth_headers).json()["membrane_connection_id"] == "remote-conn-1"
    assert client.get("/membrane/connections/by-user/missing", headers=auth_headers).status_code == 404
    assert client.get("/membrane/emails", params={"user_id": "user-1"}, headers=auth_headers).json()["total"] == 1
    assert client.get("/membrane/events", params={"user_id": "user-1"}, headers=auth_headers).json()["total"] == 1
    assert client.get("/membrane/emails/email-1", params={"user_id": "user-1"}, headers=auth_headers).json()["id"] == "email-1"
    assert client.get("/membrane/emails/missing", params={"user_id": "user-1"}, headers=auth_headers).status_code == 404
    assert client.get("/membrane/events/event-1", params={"user_id": "user-1"}, headers=auth_headers).json()["id"] == "event-1"
    assert client.get("/membrane/events/missing", params={"user_id": "user-1"}, headers=auth_headers).status_code == 404
    assert client.post(
        "/membrane/emails/send",
        json={
            "subject": "Hello",
            "body_content": "Body",
            "to_recipients": "a@example.com,b@example.com",
            "cc_recipients": "c@example.com",
            "bcc_recipients": ["b@example.com"],
        },
        headers=auth_headers,
    ).json()["status"] == "sent"
    assert client.post("/membrane/emails/email-1/reply", json={"comment": "Thanks", "reply_all": True}, headers=auth_headers).json()["status"] == "replied"
    assert route_fakes.membrane.upserted_emails[-1]["provider_message_id"].startswith("local-reply-")
    assert client.post(
        "/membrane/emails/email-1/forward",
        json={"to_recipients": "b@example.com", "comment": "FYI"},
        headers=auth_headers,
    ).json()["status"] == "forwarded"
    assert client.post("/membrane/sync-emails", headers=auth_headers).json()["synced"] == 1
    assert client.get("/membrane/config", headers=auth_headers).status_code == 200
    updated = client.put(
        "/membrane/config",
        json={"workspace_key": "workspace", "workspace_secret": "secret", "api_url": "https://api.getmembrane.test"},
        headers=auth_headers,
    ).json()
    assert updated["configured"] is True


def test_auth_dependency_accepts_and_rejects_tokens():
    token = jwt.encode({"sub": "user-1", "email": "user@example.com", "tenant_id": "tenant-1", "type": "access"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    credentials = type("Credentials", (), {"credentials": token})()
    assert get_current_user(credentials)["user_id"] == "user-1"

    invalid = type("Credentials", (), {"credentials": "not-a-token"})()
    with pytest.raises(Exception) as exc_info:
        get_current_user(invalid)
    assert getattr(exc_info.value, "status_code", None) == 401

    refresh = jwt.encode({"sub": "user-1", "type": "refresh"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(Exception) as token_type:
        get_current_user(type("Credentials", (), {"credentials": refresh})())
    assert getattr(token_type.value, "status_code", None) == 401


def test_helper_contracts():
    assert membrane_routes._build_tenant_key("tenant-1", "per-user", "user-1", "org-1") == "t:tenant-1:u:user-1"
    assert membrane_routes._build_tenant_key("tenant-1", "per-organization", "user-1", "org-1") == "t:tenant-1:o:org-1"
    assert membrane_routes._build_tenant_key("tenant-1", "per-tenant", "user-1", None) == "t:tenant-1"
    assert membrane_routes._default_scope_for("hubspot") == "per-organization"
    assert membrane_routes._parse_tenant_key("t:tenant-1:u:user-1") == ("tenant-1", "user-1")
    assert membrane_routes._extract_address({"email": "a@example.com"}) == "a@example.com"
    assert membrane_routes._extract_address("b@example.com") == "b@example.com"
    assert membrane_routes._extract_name({"name": "Ada"}) == "Ada"
    assert membrane_routes._extract_addresses([{"email": "a@example.com", "name": "A"}]) == [{"address": "a@example.com", "name": "A"}]
    assert membrane_routes._extract_attendees([{"email": "a@example.com", "status": "accepted"}])[0]["status"] == "accepted"
    assert membrane_routes._parse_iso("2026-01-01") == "2026-01-01"
    assert membrane_routes._parse_iso(object()) is None
    assert "Hello" in membrane_routes._text_preview("<p>Hello</p>")
    assert membrane_routes._text_preview(None) is None
    assert membrane_routes._text_preview("<p>" + ("x" * 600) + "</p>", max_len=10).endswith("…")
    assert ms365_routes._parse_token_expiry("2026-01-01T00:00:00+00:00").year == 2026
    with pytest.raises(Exception) as invalid_expiry:
        ms365_routes._parse_token_expiry("not-a-date")
    assert getattr(invalid_expiry.value, "status_code", None) == 400


@pytest.mark.asyncio
async def test_auth_admin_dependencies(monkeypatch):
    token = jwt.encode({"sub": "user-1", "email": "user@example.com", "type": "access"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    current = get_current_user(type("Credentials", (), {"credentials": token})())
    request = SimpleNamespace(headers={})

    async def admin_profile(user_id, forward_headers):
        return {"is_super_admin": False, "role": "admin"}

    monkeypatch.setattr(auth_module, "_fetch_user_profile", admin_profile)
    assert (await auth_module.require_admin(request, current))["role"] == "admin"

    async def user_profile(user_id, forward_headers):
        return {"is_super_admin": False, "role": "user"}

    monkeypatch.setattr(auth_module, "_fetch_user_profile", user_profile)
    with pytest.raises(Exception) as admin_denied:
        await auth_module.require_admin(request, current)
    assert getattr(admin_denied.value, "status_code", None) == 403
    with pytest.raises(Exception) as super_denied:
        await auth_module.require_super_admin(request, current)
    assert getattr(super_denied.value, "status_code", None) == 403

    async def super_profile(user_id, forward_headers):
        return {"is_super_admin": True, "role": "super_admin"}

    monkeypatch.setattr(auth_module, "_fetch_user_profile", super_profile)
    assert (await auth_module.require_super_admin(request, current))["is_super_admin"] is True


@pytest.mark.asyncio
async def test_membrane_helpers_and_sync_paths(monkeypatch):
    monkeypatch.setattr("app.infrastructure.clients.email_client.membrane_crud_client", FakeMembraneCrudClient())
    payload = membrane_routes.MembraneWebhookPayload(
        event_type="email-received",
        connection_id="remote-conn-1",
        integration_key="microsoft-outlook",
        tenant_key="t:tenant-1:u:user-1",
        data={"connectionId": "remote-conn-1", "id": "provider-email-1", "body": "<p>Preview</p>"},
    )
    await membrane_routes._handle_email_webhook(payload)
    payload.event_type = "event-created"
    payload.data = {"connectionId": "remote-conn-1", "id": "provider-event-1", "attendees": ["a@example.com"]}
    await membrane_routes._handle_event_webhook(payload)
    await membrane_routes._handle_crm_webhook(payload)
    assert await membrane_routes._resolve_local_connection(None, "user-1", "tenant-1", "microsoft-outlook") is None

    class BrokenMembraneCrud(FakeMembraneCrudClient):
        async def upsert_connection(self, data, forward_headers=None):
            raise RuntimeError("down")

    monkeypatch.setattr("app.infrastructure.clients.email_client.membrane_crud_client", BrokenMembraneCrud())
    assert await membrane_routes._resolve_local_connection("remote", "user-1", "tenant-1", "microsoft-outlook") is None

    class BrokenSettings(FakeIntegrationSettingsClient):
        async def get(self, integration_key, forward_headers=None):
            raise RuntimeError("down")

    monkeypatch.setattr(membrane_routes, "integration_settings_client", BrokenSettings())
    key = await membrane_routes._resolve_tenant_key(USER, "hubspot", request_headers={})
    assert key == "t:tenant-1:o:org-1"

    monkeypatch.setattr(membrane_sync_service, "generate_membrane_token", lambda **kwargs: "membrane-token")
    monkeypatch.setattr(membrane_sync_service, "MembraneClient", FakeMembraneClient)
    membrane_crud = FakeMembraneCrudClient()
    monkeypatch.setattr(membrane_sync_service, "membrane_crud_client", membrane_crud)
    result = await membrane_sync_service.sync_membrane_emails(
        USER,
        {"id": "local-conn-1", "membrane_connection_id": "remote-conn-1", "integration_key": "microsoft-outlook"},
        top=1,
        forward_headers={},
    )
    assert result["synced"] == 1


@pytest.mark.asyncio
async def test_ms365_sync_service_transforms_and_syncs(monkeypatch):
    assert ms365_sync_service._parse_expires_at(None).tzinfo is not None
    assert ms365_sync_service._parse_expires_at("bad").tzinfo is not None
    raw_message = {
        "id": "msg-1",
        "subject": "Hello",
        "bodyPreview": "Preview",
        "body": {"content": "<p>Hello</p>"},
        "from": {"emailAddress": {"address": "sender@example.com", "name": "Sender"}},
        "toRecipients": [{"emailAddress": {"address": "to@example.com", "name": "To"}}],
        "ccRecipients": [{"emailAddress": {"address": "cc@example.com", "name": "Cc"}}],
        "receivedDateTime": "2026-01-01T00:00:00Z",
        "isRead": True,
        "importance": "high",
        "hasAttachments": True,
        "parentFolderId": "inbox",
        "conversationId": "conv-1",
    }
    raw_event = {
        "id": "event-1",
        "subject": "Meet",
        "body": {"content": "<p>Meet</p>"},
        "location": {"displayName": "Office"},
        "start": {"dateTime": "2026-01-01T10:00:00Z"},
        "end": {"dateTime": "2026-01-01T11:00:00Z"},
        "organizer": {"emailAddress": {"address": "boss@example.com", "name": "Boss"}},
        "attendees": [{"emailAddress": {"address": "user@example.com", "name": "User"}, "status": {"response": "accepted"}}],
        "isCancelled": False,
    }
    assert ms365_sync_service._graph_msg_to_upsert(raw_message, "conn-1", "user-1")["from_address"] == "sender@example.com"
    assert ms365_sync_service._graph_event_to_upsert(raw_event, "conn-1", "user-1")["location"] == "Office"

    class FakeSyncGraph:
        def __init__(self):
            self._last_delta_token = None

        async def ensure_valid_token(self, access_token, refresh_token, expires_at):
            return "access-token", {"access_token": "new-token"}

        async def get_emails_batched(self, access_token, delta_token=None):
            self._last_delta_token = "delta-email"
            yield [raw_message], 1, 1

        async def get_calendar_events(self, access_token, delta_token=None):
            return [raw_event], "delta-calendar"

    class RecordingConnectionClient(FakeConnectionClient):
        def __init__(self):
            self.updates = []

        async def update(self, conn_id, data, forward_headers=None):
            self.updates.append((conn_id, data))
            return connection_payload(id=conn_id, **data)

    conn_client = RecordingConnectionClient()
    email_client = FakeEmailCrudClient()
    event_client = FakeEventCrudClient()
    monkeypatch.setattr("app.infrastructure.external.ms365_graph_service.MS365GraphService", FakeSyncGraph)
    monkeypatch.setattr(ms365_sync_service, "connection_client", conn_client)
    monkeypatch.setattr(ms365_sync_service, "email_crud_client", email_client)
    monkeypatch.setattr(ms365_sync_service, "event_crud_client", event_client)
    service = ms365_sync_service.MS365SyncService(forward_headers={})
    conn = connection_payload(id="conn-1", token_expires_at="2020-01-01T00:00:00+00:00")
    assert await service.sync_emails(conn) == 1
    assert await service.sync_calendar(conn) == 1
    await service.handle_webhook_notification([{"resource": "me/messages"}])
    assert any("email_delta_token" in update for _, update in conn_client.updates)


def install_async_client_queue(monkeypatch, module, responses):
    calls = []
    queue = list(responses)

    class QueuedAsyncClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, **kwargs):
            calls.append(("get", url, kwargs))
            return queue.pop(0)

        async def post(self, url, **kwargs):
            calls.append(("post", url, kwargs))
            return queue.pop(0)

        async def patch(self, url, **kwargs):
            calls.append(("patch", url, kwargs))
            return queue.pop(0)

        async def delete(self, url, **kwargs):
            calls.append(("delete", url, kwargs))
            return queue.pop(0)

        async def request(self, method, url, **kwargs):
            calls.append((method.lower(), url, kwargs))
            return queue.pop(0)

        async def aclose(self):
            calls.append(("close", "", {}))

    monkeypatch.setattr(module.httpx, "AsyncClient", QueuedAsyncClient)
    return calls


@pytest.mark.asyncio
async def test_membrane_service_client_and_url_contracts(monkeypatch):
    runtime_settings = settings.model_copy(
        update={
            "membrane_workspace_key": "workspace",
            "membrane_workspace_secret": "secret",
            "membrane_client_token": "client-token",
            "membrane_api_url": "https://api.getmembrane.test",
        }
    )
    monkeypatch.setattr(membrane_service, "_settings", runtime_settings)
    membrane_service.set_membrane_credentials("workspace-2", "secret-2", "https://api2.getmembrane.test", "client-token-2")
    token = membrane_service.generate_membrane_token(
        tenant_key="t:tenant-1:u:user-1",
        name="user@example.com",
        fields={"croo_user_id": "user-1"},
        expires_minutes=5,
    )
    assert token
    assert "integrationKey=microsoft-outlook" in membrane_service.build_connect_url("microsoft-outlook", "token", "https://app.example.test")
    assert "connectionId=remote-conn-1" in membrane_service.build_reconnect_url("remote-conn-1", "token", "https://app.example.test")

    responses = [
        FakeResponse({"items": [{"key": "microsoft-outlook"}]}),
        FakeResponse({"items": [{"id": "remote-conn-1"}]}),
        FakeResponse(status_code=404),
        FakeResponse({"id": "remote-conn-1"}),
        FakeResponse({"ok": True}),
        FakeResponse(status_code=404),
        FakeResponse({"deleted": True}),
        FakeResponse({"value": [1]}),
        FakeResponse(None, status_code=204),
        FakeResponse({"sent": True}),
    ]
    calls = install_async_client_queue(monkeypatch, membrane_service, responses)
    client = membrane_service.MembraneClient("tenant-token")
    assert await client.list_integrations() == [{"key": "microsoft-outlook"}]
    assert await client.list_connections() == [{"id": "remote-conn-1"}]
    assert await client.get_connection("missing") is None
    assert (await client.get_connection("remote-conn-1"))["id"] == "remote-conn-1"
    assert (await client.run_action("send-email", {"subject": "Hi"}, "remote-conn-1"))["ok"] is True
    assert await client.delete_connection("missing") is False
    assert await client.delete_connection("remote-conn-1") is True
    assert (await client.proxy_get("remote-conn-1", "/me/messages", {"$top": "1"}))["value"] == [1]
    assert await client.proxy_post("remote-conn-1", "/me/sendMail", {"message": {}}) == {}
    assert (await client.proxy_post("remote-conn-1", "/me/sendMail", {"message": {}}))["sent"] is True
    await client.close()
    assert calls[-1][0] == "close"


@pytest.mark.asyncio
async def test_ms365_graph_service_client_contracts(monkeypatch):
    service = ms365_graph_service.MS365GraphService()
    service._client_id = "client-id"
    service._client_secret = "client-secret"
    service._redirect_uri = "https://api.example.test/callback"
    assert "state=user-1" in service.build_auth_url("user-1")

    responses = [
        FakeResponse({"access_token": "access-token", "refresh_token": "refresh-token"}),
        FakeResponse({"access_token": "refreshed-token"}),
        FakeResponse({"id": "ms-user-1"}),
        FakeResponse({"value": [{"id": "msg-1"}], "@odata.nextLink": "next-page"}),
        FakeResponse({"value": [{"id": "msg-2"}], "@odata.deltaLink": "delta-link"}),
        FakeResponse({"value": [], "@odata.nextLink": "next-delta"}),
        FakeResponse({"value": [], "@odata.deltaLink": "delta-acquired"}),
        FakeResponse({"value": [{"id": "event-1"}], "@odata.deltaLink": "event-delta"}),
        FakeResponse({}),
        FakeResponse({}),
        FakeResponse({}),
        FakeResponse({"id": "sub-1"}),
        FakeResponse({"id": "sub-1", "renewed": True}),
    ]
    calls = install_async_client_queue(monkeypatch, ms365_graph_service, responses)

    assert (await service.exchange_code_for_tokens("code"))["access_token"] == "access-token"
    assert (await service.refresh_access_token("refresh-token"))["access_token"] == "refreshed-token"
    assert (await service.get_user_profile("access-token"))["id"] == "ms-user-1"

    pages = []
    async for messages, page, total in service.get_emails_batched("access-token", top=1):
        pages.append((messages, page, total))
    assert [message["id"] for messages, _, _ in pages for message in messages] == ["msg-1", "msg-2"]
    assert service._last_delta_token == "delta-link"

    service_for_delta = ms365_graph_service.MS365GraphService()
    assert await service_for_delta.acquire_delta_token("access-token") == "delta-acquired"
    events, event_delta = await service.get_calendar_events("access-token", top=1)
    assert events[0]["id"] == "event-1"
    assert event_delta == "event-delta"

    assert (await service.send_mail("access-token", "Hi", "Body", ["a@example.com"], ["c@example.com"], ["b@example.com"]))["status"] == "sent"
    assert (await service.reply_mail("access-token", "msg-1", "Thanks", reply_all=True))["status"] == "sent"
    assert (await service.forward_mail("access-token", "msg-1", ["b@example.com"], "FYI"))["status"] == "sent"
    assert (await service.create_webhook_subscription("access-token", "me/messages", "https://callback"))["id"] == "sub-1"
    assert (await service.renew_webhook_subscription("access-token", "sub-1"))["renewed"] is True

    valid_token, new_data = await service.ensure_valid_token(
        "still-valid",
        "refresh-token",
        datetime.now(timezone.utc) + timedelta(hours=1),
    )
    assert valid_token == "still-valid"
    assert new_data is None

    async def fake_refresh(refresh_token):
        return {"access_token": "new-access"}

    monkeypatch.setattr(service, "refresh_access_token", fake_refresh)
    refreshed, refreshed_data = await service.ensure_valid_token(
        "expired",
        "refresh-token",
        datetime.now(timezone.utc) - timedelta(hours=1),
    )
    assert refreshed == "new-access"
    assert refreshed_data["access_token"] == "new-access"
    assert any(call[0] == "post" for call in calls)


@pytest.mark.asyncio
async def test_backend_client_methods_cover_paths(monkeypatch):
    services = {}

    def fake_factory(name):
        services.setdefault(name, FakeServiceClient(name))
        return services[name]

    monkeypatch.setattr("app.infrastructure.clients.email_client.create_service_client", fake_factory)

    integration_client = IntegrationSettingsClient()
    connection_client = ConnectionClient()
    email_client = EmailCrudClient()
    event_client = EventCrudClient()
    label_client = SmartLabelClient()
    membrane_client = MembraneCrudClient()

    assert (await integration_client.list())[0]["integration_key"] == "microsoft-outlook"
    assert (await integration_client.upsert({"integration_key": "gmail"}))["integration_key"] == "gmail"
    assert (await integration_client.get("microsoft-outlook"))["id"] == "setting-1"
    assert await integration_client.get("unknown") is None
    assert (await integration_client.update("gmail", {"scope_mode": "per-tenant"}))["scope_mode"] == "per-tenant"
    assert await integration_client.delete("gmail") is True

    assert (await connection_client.get_by_user("user-1"))["user_id"] == "user-1"
    assert await connection_client.get_by_user("missing") is None
    with pytest.raises(Exception) as conn_error:
        await connection_client.get_by_user("boom")
    assert "CONN_CLIENT|500" in str(conn_error.value)
    assert await connection_client.get("missing") is None
    assert (await connection_client.get("conn-1"))["id"] == "conn-1"
    assert len(await connection_client.list_active()) == 1
    assert (await connection_client.create({"user_id": "user-1"}))["user_id"] == "user-1"
    assert (await connection_client.update("conn-1", {"is_active": False}))["is_active"] is False
    assert await connection_client.delete("conn-1") is True

    assert (await email_client.list("user-1", 1, 2, "inbox", "hello", "Client", "contact-1"))["limit"] == 2
    assert await email_client.get("missing", "user-1") is None
    assert (await email_client.get("email-1", "user-1"))["id"] == "email-1"
    assert (await email_client.upsert({"subject": "Hi"}))["subject"] == "Hi"
    assert (await email_client.update("email-1", {"is_read": True}, "user-1"))["is_read"] is True
    assert await email_client.delete("email-1", "user-1") is True

    assert (await event_client.list("user-1", 1, 2, datetime.now(timezone.utc), datetime.now(timezone.utc)))["limit"] == 2
    assert await event_client.get("missing", "user-1") is None
    assert (await event_client.get("event-1", "user-1"))["id"] == "event-1"
    assert (await event_client.upsert({"subject": "Meet"}))["subject"] == "Meet"
    assert (await event_client.update("event-1", {"subject": "Updated"}, "user-1"))["subject"] == "Updated"
    assert await event_client.delete("event-1", "user-1") is True

    assert (await label_client.list())["total"] == 1
    assert await label_client.get("missing") is None
    assert (await label_client.get("label-1"))["id"] == "label-1"
    assert (await label_client.create({"name": "Client"}))["name"] == "Client"
    assert (await label_client.update("label-1", {"color": "#fff"}))["color"] == "#fff"
    assert await label_client.delete("label-1") is True

    assert (await membrane_client.upsert_connection({"user_id": "user-1"}))["user_id"] == "user-1"
    assert await membrane_client.get_connection("missing") is None
    assert (await membrane_client.get_connection("local-conn-1"))["id"] == "local-conn-1"
    assert (await membrane_client.upsert_email({"subject": "Hi"}))["subject"] == "Hi"
    assert (await membrane_client.upsert_event({"subject": "Meet"}))["subject"] == "Meet"
    assert await membrane_client.get_connection_by_user("missing") is None
    assert (await membrane_client.get_connection_by_user("user-1", "microsoft-outlook"))["membrane_connection_id"] == "remote-conn-1"
    assert (await membrane_client.list_emails("user-1", folder="inbox", search="hello"))["total"] == 1
    assert await membrane_client.get_email("missing", "user-1") is None
    assert (await membrane_client.get_email("email-1", "user-1"))["id"] == "email-1"
    assert await membrane_client.get_event("missing", "user-1") is None
    assert (await membrane_client.get_event("event-1", "user-1"))["id"] == "event-1"
    assert (await membrane_client.list_events("user-1", from_date="2026-01-01", to_date="2026-01-02"))["total"] == 1


def test_python_package_contract_loads_runtime_components():
    from communication_b4f_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (
        ms365_routes,
        smart_label_routes,
        webhook_routes,
        membrane_routes,
        integration_settings_routes,
    )
    assert contract.load_runtime_client_classes() == (
        IntegrationSettingsClient,
        ConnectionClient,
        EmailCrudClient,
        EventCrudClient,
        SmartLabelClient,
        MembraneCrudClient,
    )


@pytest.mark.asyncio
async def test_unmounted_membrane_email_routes_directly(monkeypatch):
    monkeypatch.setattr(membrane_email_routes, "generate_membrane_token", lambda **kwargs: "membrane-token")
    monkeypatch.setattr(membrane_email_routes, "MembraneClient", FakeMembraneClient)
    monkeypatch.setattr(membrane_email_routes, "email_crud_client", FakeEmailCrudClient())
    monkeypatch.setattr(membrane_email_routes, "event_crud_client", FakeEventCrudClient())
    request = SimpleNamespace(headers={})

    assert membrane_email_routes._resolve_email_tenant_key(USER) == "user-1"
    assert (await membrane_email_routes._get_email_connection(USER))["id"] == "remote-conn-1"
    listed = await membrane_email_routes.list_emails(request, current_user=USER)
    assert listed["total"] == 1
    events = await membrane_email_routes.list_events(request, current_user=USER)
    assert events["total"] == 1
    sent = await membrane_email_routes.send_email(
        ms365_routes.SendEmailRequest(subject="Hi", body_content="Body", to_recipients=["a@example.com"]),
        request,
        USER,
    )
    assert sent["status"] == "sent"
    replied = await membrane_email_routes.reply_email("email-1", ms365_routes.ReplyEmailRequest(comment="Thanks"), request, USER)
    assert replied["status"] == "replied"
    forwarded = await membrane_email_routes.forward_email(
        "email-1",
        ms365_routes.ForwardEmailRequest(to_recipients=["b@example.com"], comment="FYI"),
        request,
        USER,
    )
    assert forwarded["status"] == "forwarded"
