from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.infrastructure.persistence.models.integration_setting import IntegrationSetting
from app.infrastructure.persistence.models.membrane_connection import MembraneConnection
from app.infrastructure.persistence.models.membrane_synced_email import MembraneSyncedEmail
from app.infrastructure.persistence.models.membrane_synced_event import MembraneSyncedEvent
from app.infrastructure.persistence.models.ms365_connection import MS365Connection
from app.infrastructure.persistence.models.smart_label import SmartLabel
from app.infrastructure.persistence.models.synced_email import SyncedEmail
from app.infrastructure.persistence.models.synced_event import SyncedEvent
from app.events import publishers
from app.infrastructure import database
from app.infrastructure.persistence.integration_settings_repository import IntegrationSettingsRepository
from app.infrastructure.persistence.membrane_repository import MembraneRepository
from app.infrastructure.persistence.ms365_repository import MS365Repository
from app.infrastructure.persistence.smart_label_repository import SmartLabelRepository
from app.middleware import auth
from app.middleware.auth import get_current_user, settings
from app.presentation import deps as email_deps
from app.presentation.routes import (
    connection_routes,
    email_contact_routes,
    email_routes,
    event_routes,
    integration_settings_routes,
    membrane_routes,
    provider_membrane_routes,
    provider_ms365_routes,
    smart_label_routes,
)
from app.presentation.schemas import integration_settings_schemas, membrane_schemas, ms365_schemas, smart_label_schemas


USER = {"user_id": "user-1", "email": "email@example.com", "tenant_id": "tenant-1", "role": "", "is_super_admin": False}
ADMIN = {**USER, "role": "admin", "is_super_admin": False}
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def stamp(entity):
    entity.created_at = NOW
    entity.updated_at = NOW
    entity.version = 1
    entity.is_deleted = False
    entity.deleted_at = None
    entity.deleted_by = None
    return entity


def make_connection(conn_id="conn-1", **overrides):
    conn = MS365Connection(
        id=conn_id,
        user_id="user-1",
        ms_user_id="ms-user-1",
        ms_email="ada@example.com",
        access_token="access",
        refresh_token="refresh",
        token_expires_at=NOW + timedelta(hours=1),
        scopes="Mail.Read Calendars.Read",
        is_active=True,
        connection_status="active",
        tenant_id="tenant-1",
    )
    conn.last_email_sync = NOW
    conn.last_calendar_sync = NOW
    conn.email_delta_token = "email-delta"
    conn.calendar_delta_token = "calendar-delta"
    conn.email_webhook_subscription_id = "email-sub"
    conn.calendar_webhook_subscription_id = "calendar-sub"
    for key, value in overrides.items():
        setattr(conn, key, value)
    return stamp(conn)


def make_email(email_id="email-1", **overrides):
    email = SyncedEmail(
        id=email_id,
        ms365_connection_id="conn-1",
        user_id="user-1",
        ms_message_id="message-1",
        subject="Hello",
        body_preview="Preview",
        body_html="<p>Hello</p>",
        from_address="sender@example.com",
        from_name="Sender",
        to_addresses=[{"address": "ada@example.com", "name": "Ada"}],
        cc_addresses=[],
        received_at=NOW,
        is_read=False,
        importance="normal",
        has_attachments=False,
        attachments_meta=[],
        folder="inbox",
        smart_label="priority",
        ai_summary="Summary",
        ai_action_items=["reply"],
        conversation_id="conversation-1",
        linked_contact_id="contact-1",
        linked_organization_id="org-1",
        tenant_id="tenant-1",
    )
    for key, value in overrides.items():
        setattr(email, key, value)
    return stamp(email)


def make_event(event_id="event-1", **overrides):
    event = SyncedEvent(
        id=event_id,
        ms365_connection_id="conn-1",
        user_id="user-1",
        ms_event_id="ms-event-1",
        subject="Demo",
        body_html="<p>Demo</p>",
        location="Teams",
        start_time=NOW,
        end_time=NOW + timedelta(hours=1),
        is_all_day=False,
        organizer_email="organizer@example.com",
        organizer_name="Organizer",
        attendees=[{"email": "ada@example.com", "status": "accepted"}],
        status="accepted",
        is_cancelled=False,
        recurrence=None,
        online_meeting_url="https://meet.example.com",
        linked_contact_id="contact-1",
        linked_organization_id="org-1",
        tenant_id="tenant-1",
    )
    for key, value in overrides.items():
        setattr(event, key, value)
    return stamp(event)


def make_smart_label(label_id="label-1", **overrides):
    label = SmartLabel(
        id=label_id,
        name="Priority",
        color="#ff0000",
        description="Important email",
        keywords=["urgent"],
        prompt_hint="Classify urgent requests",
        parent_id=None,
        tenant_id="tenant-1",
        created_by="email@example.com",
    )
    label.sub_labels = []
    label.parent = None
    for key, value in overrides.items():
        setattr(label, key, value)
    return stamp(label)


def make_integration(setting_id="setting-1", **overrides):
    setting = IntegrationSetting(
        id=setting_id,
        integration_key="microsoft-outlook",
        scope_mode="per-user",
        is_enabled=True,
        display_name="Outlook",
        notes="Tenant default",
        tenant_id="tenant-1",
    )
    for key, value in overrides.items():
        setattr(setting, key, value)
    stamp(setting)
    setting.created_at = NOW.isoformat()
    setting.updated_at = NOW.isoformat()
    return setting


def make_membrane_connection(conn_id="membrane-conn-1", **overrides):
    conn = MembraneConnection(
        id=conn_id,
        user_id="user-1",
        membrane_connection_id="membrane-provider-1",
        integration_key="microsoft-outlook",
        connection_name="Outlook",
        is_active=True,
        metadata_json=None,
        tenant_id="tenant-1",
    )
    conn.last_email_sync = NOW
    conn.last_calendar_sync = NOW
    for key, value in overrides.items():
        setattr(conn, key, value)
    return stamp(conn)


def make_membrane_email(email_id="membrane-email-1", **overrides):
    email = MembraneSyncedEmail(
        id=email_id,
        membrane_connection_id="membrane-conn-1",
        user_id="user-1",
        provider_message_id="provider-message-1",
        provider="microsoft-outlook",
        subject="Membrane hello",
        body_preview="Preview",
        body_html="<p>Hello</p>",
        from_address="sender@example.com",
        from_name="Sender",
        to_addresses=[],
        cc_addresses=[],
        received_at=NOW,
        is_read=False,
        importance="normal",
        has_attachments=False,
        attachments_meta=[],
        folder="inbox",
        conversation_id="conversation-1",
        linked_contact_id="contact-1",
        linked_organization_id="org-1",
        tenant_id="tenant-1",
    )
    for key, value in overrides.items():
        setattr(email, key, value)
    return stamp(email)


def make_membrane_event(event_id="membrane-event-1", **overrides):
    event = MembraneSyncedEvent(
        id=event_id,
        membrane_connection_id="membrane-conn-1",
        user_id="user-1",
        provider_event_id="provider-event-1",
        provider="microsoft-outlook",
        subject="Membrane demo",
        body_html="<p>Demo</p>",
        location="Teams",
        start_time=NOW,
        end_time=NOW + timedelta(hours=1),
        is_all_day=False,
        organizer_email="organizer@example.com",
        organizer_name="Organizer",
        attendees=[],
        status="accepted",
        is_cancelled=False,
        recurrence=None,
        online_meeting_url="https://meet.example.com",
        linked_contact_id="contact-1",
        linked_organization_id="org-1",
        tenant_id="tenant-1",
    )
    for key, value in overrides.items():
        setattr(event, key, value)
    return stamp(event)


class FakeQuery:
    def __init__(self, items=None):
        self.items = list(items or [])

    def filter(self, *args):
        return self

    def join(self, *args):
        return self

    def options(self, *args):
        return self

    def order_by(self, *args):
        return self

    def offset(self, skip):
        self.items = self.items[skip:]
        return self

    def limit(self, limit):
        self.items = self.items[:limit]
        return self

    def first(self):
        return self.items[0] if self.items else None

    def all(self):
        return self.items

    def count(self):
        return len(self.items)


class FakeResult:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def fetchall(self):
        return self.rows


class FakeDB:
    def __init__(self):
        self.added = []
        self.deleted = []
        self.commits = 0
        self.refreshes = 0
        self.executed = []
        self.connection = make_connection()
        self.email = make_email()
        self.event = make_event()
        self.label = make_smart_label()
        self.integration = make_integration()
        self.membrane_connection = make_membrane_connection()
        self.membrane_email = make_membrane_email()
        self.membrane_event = make_membrane_event()
        self.storage = {
            MS365Connection: [self.connection],
            SyncedEmail: [self.email],
            SyncedEvent: [self.event],
            SmartLabel: [self.label],
            IntegrationSetting: [self.integration],
            MembraneConnection: [self.membrane_connection],
            MembraneSyncedEmail: [self.membrane_email],
            MembraneSyncedEvent: [self.membrane_event],
        }

    def query(self, entity):
        return FakeQuery(self.storage.get(entity, []))

    def add(self, entity):
        self.added.append(entity)
        if not getattr(entity, "id", None):
            entity.id = f"{entity.__class__.__name__.lower()}-{len(self.added)}"
        if not getattr(entity, "tenant_id", None):
            entity.tenant_id = "tenant-1"
        entity.created_at = getattr(entity, "created_at", None) or NOW
        entity.updated_at = getattr(entity, "updated_at", None) or NOW
        entity.version = getattr(entity, "version", None) or 1
        entity.is_deleted = getattr(entity, "is_deleted", None) or False
        self.storage.setdefault(entity.__class__, []).append(entity)

    def commit(self):
        self.commits += 1

    def refresh(self, entity):
        self.refreshes += 1
        if not getattr(entity, "id", None):
            entity.id = f"{entity.__class__.__name__.lower()}-{self.refreshes}"
        entity.created_at = getattr(entity, "created_at", None) or NOW
        entity.updated_at = getattr(entity, "updated_at", None) or NOW
        entity.version = getattr(entity, "version", None) or 1
        entity.is_deleted = getattr(entity, "is_deleted", None) or False

    def delete(self, entity):
        self.deleted.append(entity)

    def rollback(self):
        return None

    def execute(self, statement):
        self.executed.append(statement)
        return FakeResult(
            [
                SimpleNamespace(
                    id="email-contact-1",
                    synced_email_id="email-1",
                    contact_id="contact-1",
                    role="from",
                )
            ]
        )

    def close(self):
        return None


class EmptyDB(FakeDB):
    def __init__(self):
        super().__init__()
        self.storage = {}


class FakeMS365Repository:
    def __init__(self, db):
        self.db = db
        self.connection = make_connection()
        self.email = make_email()
        self.event = make_event()
        self.links = [
            SimpleNamespace(id="email-contact-1", synced_email_id="email-1", contact_id="contact-1", role="from")
        ]

    def get_connection_by_user(self, user_id, tenant_id):
        return self.connection if user_id == "user-1" else None

    def get_connection_by_id(self, conn_id, tenant_id):
        return self.connection if conn_id == "conn-1" else None

    def get_all_active_connections(self):
        return [self.connection]

    def create_connection(self, data, tenant_id):
        self.connection = make_connection("conn-new", tenant_id=tenant_id, **data)
        return self.connection

    def update_connection(self, conn, data):
        for key, value in data.items():
            setattr(conn, key, value)
        conn.version += 1
        return conn

    def soft_delete_connection(self, conn, deleted_by):
        conn.is_deleted = True
        conn.is_active = False
        conn.deleted_by = deleted_by
        return conn

    def list_emails(self, *args):
        return [self.email]

    def count_emails(self, *args):
        return 1

    def get_email_by_id(self, email_id, user_id, tenant_id):
        return self.email if email_id == "email-1" else None

    def upsert_email(self, data, tenant_id):
        self.email = make_email("email-new", tenant_id=tenant_id, **data)
        return self.email

    def update_email(self, email, data):
        for key, value in data.items():
            setattr(email, key, value)
        return email

    def delete_email(self, email):
        self.deleted_email = email.id

    def list_events(self, *args):
        return [self.event]

    def count_events(self, *args):
        return 1

    def get_event_by_id(self, event_id, user_id, tenant_id):
        return self.event if event_id == "event-1" else None

    def upsert_event(self, data, tenant_id):
        self.event = make_event("event-new", tenant_id=tenant_id, **data)
        return self.event

    def update_event(self, event, data):
        for key, value in data.items():
            setattr(event, key, value)
        return event

    def delete_event(self, event):
        self.deleted_event = event.id

    def get_email_contacts(self, email_id):
        return self.links

    def link_email_contact(self, email_id, contact_id, role):
        self.linked = (email_id, contact_id, role)

    def unlink_email_contact(self, email_id, contact_id):
        self.unlinked = (email_id, contact_id)


class FakeSmartLabelRepository:
    def __init__(self, db):
        self.db = db
        self.label = make_smart_label()

    def get_by_name(self, name, tenant_id, parent_id=None):
        return self.label if name == "Duplicate" else None

    def create(self, label):
        label.id = "label-new"
        label.tenant_id = "tenant-1"
        return stamp(label)

    def list_all(self, tenant_id, skip=0, limit=50):
        return [self.label]

    def count(self, tenant_id):
        return 1

    def get_by_id(self, label_id, tenant_id):
        return self.label if label_id == "label-1" else None

    def update(self, label):
        label.version += 1
        return label

    def delete(self, label):
        self.deleted = label.id


class FakeIntegrationSettingsRepository:
    def __init__(self, db):
        self.db = db
        self.setting = make_integration()

    def list_settings(self, tenant_id):
        return [self.setting]

    def upsert_setting(self, tenant_id, integration_key, data):
        payload = {**data, "tenant_id": tenant_id, "integration_key": integration_key}
        self.setting = make_integration(**payload)
        return self.setting

    def get_setting(self, tenant_id, integration_key):
        return self.setting if integration_key == "microsoft-outlook" else None

    def delete_setting(self, tenant_id, integration_key):
        return integration_key == "microsoft-outlook"


class FakeMembraneRepository:
    def __init__(self, db):
        self.db = db
        self.connection = make_membrane_connection()
        self.email = make_membrane_email()
        self.event = make_membrane_event()

    def get_connection_by_user_integration(self, user_id, integration_key, tenant_id):
        return self.connection if user_id == "user-1" and integration_key == "microsoft-outlook" else None

    def create_connection(self, data, tenant_id):
        return make_membrane_connection("membrane-new", tenant_id=tenant_id, **data)

    def update_connection(self, conn, data):
        for key, value in data.items():
            setattr(conn, key, value)
        conn.version += 1
        return conn

    def soft_delete_connection(self, conn, deleted_by):
        conn.is_deleted = True
        conn.is_active = False
        return conn

    def upsert_email(self, data, tenant_id):
        return make_membrane_email("membrane-email-new", tenant_id=tenant_id, **data)

    def list_emails(self, *args):
        return [self.email]

    def count_emails(self, *args):
        return 1

    def get_email_by_id(self, email_id, user_id, tenant_id):
        return self.email if email_id == "membrane-email-1" else None

    def upsert_event(self, data, tenant_id):
        return make_membrane_event("membrane-event-new", tenant_id=tenant_id, **data)

    def list_events(self, *args):
        return [self.event]

    def count_events(self, *args):
        return 1

    def get_event_by_id(self, event_id, user_id, tenant_id):
        return self.event if event_id == "membrane-event-1" else None


@pytest.fixture()
def fake_db():
    return FakeDB()


@pytest.fixture()
def client(monkeypatch, fake_db):
    ms365_repo = FakeMS365Repository(fake_db)
    label_repo = FakeSmartLabelRepository(fake_db)
    settings_repo = FakeIntegrationSettingsRepository(fake_db)
    membrane_repo = FakeMembraneRepository(fake_db)

    async def noop_publish(*args, **kwargs):
        return None

    monkeypatch.setattr(email_deps, "MS365Repository", lambda db: ms365_repo)
    monkeypatch.setattr(email_deps, "publish_email_received", noop_publish)
    monkeypatch.setattr(email_deps, "SmartLabelRepository", lambda db: label_repo)
    monkeypatch.setattr(email_deps, "IntegrationSettingsRepository", lambda db: settings_repo)
    monkeypatch.setattr(membrane_routes, "MembraneRepository", lambda db: membrane_repo)

    for module in (
        connection_routes,
        email_routes,
        event_routes,
        email_contact_routes,
        smart_label_routes,
        integration_settings_routes,
        membrane_routes,
    ):
        main.app.dependency_overrides[module.get_current_user] = lambda: USER
        if hasattr(module, "get_db"):
            main.app.dependency_overrides[module.get_db] = lambda: fake_db
    main.app.dependency_overrides[email_deps.get_db] = lambda: fake_db
    main.app.dependency_overrides[integration_settings_routes.require_admin] = lambda: ADMIN

    test_client = TestClient(main.app)
    yield test_client
    test_client.close()
    main.app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers():
    token = jwt.encode(
        {"sub": "user-1", "email": "email@example.com", "tenant_id": "tenant-1"},
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


def test_auth_dependency_accepts_and_rejects_tokens(auth_headers):
    credentials = type("Credentials", (), {"credentials": auth_headers["Authorization"].split(" ", 1)[1]})()
    assert get_current_user(credentials)["tenant_id"] == "tenant-1"

    invalid = type("Credentials", (), {"credentials": "not-a-token"})()
    with pytest.raises(Exception) as invalid_token:
        get_current_user(invalid)
    assert getattr(invalid_token.value, "status_code", None) == 401

    no_sub = jwt.encode({"email": "email@example.com"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(Exception) as missing_sub:
        get_current_user(type("Credentials", (), {"credentials": no_sub})())
    assert getattr(missing_sub.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_require_admin_uses_signed_claims_without_backend_http():
    assert (await auth.require_admin(ADMIN))["role"] == "admin"
    assert (await auth.require_admin({**USER, "is_super_admin": True}))["is_super_admin"] is True

    with pytest.raises(HTTPException) as denied:
        await auth.require_admin({**USER, "role": "member"})
    assert denied.value.status_code == 403


def test_connection_routes(client):
    assert client.get("/api/v1/connections/by-user/user-1").json()["id"] == "conn-1"
    assert client.get("/api/v1/connections/by-user/missing").json() is None
    assert client.get("/api/v1/connections/conn-1").json()["ms_email"] == "ada@example.com"
    assert client.get("/api/v1/connections/missing").status_code == 404
    assert client.get("/api/v1/connections/active/all").json()[0]["id"] == "conn-1"
    created = client.post(
        "/api/v1/connections",
        json={"user_id": "user-new", "ms_email": "new@example.com", "is_active": True},
    )
    assert created.status_code == 201
    assert created.json()["id"] == "conn-new"
    assert client.post("/api/v1/connections", json={"user_id": "user-1"}).status_code == 409
    assert client.patch("/api/v1/connections/conn-1", json={"is_active": False}).json()["is_active"] is False
    assert client.patch("/api/v1/connections/missing", json={"is_active": False}).status_code == 404
    assert client.delete("/api/v1/connections/conn-1").status_code == 204
    assert client.delete("/api/v1/connections/missing").status_code == 404


def test_email_event_and_contact_routes(client):
    assert client.get("/api/v1/emails", params={"user_id": "user-1", "search": "Hello"}).json()["total"] == 1
    assert client.get("/api/v1/emails/email-1", params={"user_id": "user-1"}).json()["subject"] == "Hello"
    assert client.get("/api/v1/emails/missing", params={"user_id": "user-1"}).status_code == 404
    created = client.post(
        "/api/v1/emails",
        json={
            "ms365_connection_id": "conn-1",
            "user_id": "user-1",
            "ms_message_id": "message-new",
            "subject": "New",
            "from_address": "sender@example.com",
        },
    )
    assert created.status_code == 201
    assert created.json()["id"] == "email-new"
    assert client.patch("/api/v1/emails/email-1", params={"user_id": "user-1"}, json={"is_read": True}).json()["is_read"] is True
    assert client.patch("/api/v1/emails/missing", params={"user_id": "user-1"}, json={"is_read": True}).status_code == 404
    assert client.delete("/api/v1/emails/email-1", params={"user_id": "user-1"}).status_code == 204
    assert client.delete("/api/v1/emails/missing", params={"user_id": "user-1"}).status_code == 404

    assert client.get("/api/v1/events", params={"user_id": "user-1"}).json()["total"] == 1
    assert client.get("/api/v1/events/event-1", params={"user_id": "user-1"}).json()["subject"] == "Demo"
    assert client.get("/api/v1/events/missing", params={"user_id": "user-1"}).status_code == 404
    event = client.post(
        "/api/v1/events",
        json={"ms365_connection_id": "conn-1", "user_id": "user-1", "ms_event_id": "event-new", "subject": "New"},
    )
    assert event.status_code == 201
    assert client.patch("/api/v1/events/event-1", params={"user_id": "user-1"}, json={"location": "Office"}).json()["location"] == "Office"
    assert client.delete("/api/v1/events/event-1", params={"user_id": "user-1"}).status_code == 204

    assert client.get("/api/v1/emails/email-1/contacts").json()[0]["contact_id"] == "contact-1"
    assert client.post("/api/v1/emails/email-1/contacts", json={"contact_id": "contact-2", "role": "to"}).json()["status"] == "linked"
    assert client.delete("/api/v1/emails/email-1/contacts/contact-2").status_code == 204


def test_smart_label_and_integration_settings_routes(client):
    assert client.post("/api/v1/smart-labels", json={"name": "Priority", "color": " #00ff00 "}).json()["id"] == "label-new"
    assert client.post("/api/v1/smart-labels", json={"name": "Duplicate"}).status_code == 400
    assert client.get("/api/v1/smart-labels").json()["total"] == 1
    assert client.get("/api/v1/smart-labels/label-1").json()["name"] == "Priority"
    assert client.get("/api/v1/smart-labels/missing").status_code == 404
    assert client.patch("/api/v1/smart-labels/label-1", json={"description": "Updated"}).json()["description"] == "Updated"
    assert client.patch("/api/v1/smart-labels/missing", json={"description": "Updated"}).status_code == 404
    assert client.delete("/api/v1/smart-labels/label-1").status_code == 204
    assert client.delete("/api/v1/smart-labels/missing").status_code == 404

    assert client.get("/api/v1/integration-settings").json()["items"][0]["integration_key"] == "microsoft-outlook"
    created = client.post(
        "/api/v1/integration-settings",
        json={"integration_key": "microsoft-outlook", "display_name": "Outlook"},
    )
    assert created.status_code == 201
    assert client.patch("/api/v1/integration-settings/microsoft-outlook", json={"is_enabled": False}).json()["is_enabled"] is False
    assert client.patch("/api/v1/integration-settings/missing", json={"is_enabled": False}).status_code == 404
    assert client.delete("/api/v1/integration-settings/microsoft-outlook").status_code == 204
    assert client.delete("/api/v1/integration-settings/missing").status_code == 404


def test_membrane_routes(client):
    created = client.post(
        "/api/v1/membrane/connections",
        json={
            "user_id": "user-new",
            "membrane_connection_id": "membrane-new",
            "integration_key": "microsoft-outlook",
            "connection_name": "Outlook",
        },
    )
    assert created.status_code == 201
    assert client.post(
        "/api/v1/membrane/connections",
        json={
            "user_id": "user-1",
            "membrane_connection_id": "membrane-provider-1",
            "integration_key": "microsoft-outlook",
        },
    ).json()["id"] == "membrane-conn-1"
    assert client.get(
        "/api/v1/membrane/connections/by-user/user-1",
        params={"integration_key": "microsoft-outlook"},
    ).json()["id"] == "membrane-conn-1"
    assert client.get("/api/v1/membrane/connections/membrane-conn-1").json()["integration_key"] == "microsoft-outlook"
    assert client.patch(
        "/api/v1/membrane/connections/membrane-conn-1",
        json={
            "user_id": "user-1",
            "membrane_connection_id": "membrane-provider-1",
            "integration_key": "microsoft-outlook",
            "connection_name": "Updated",
        },
    ).json()["connection_name"] == "Updated"
    assert client.delete("/api/v1/membrane/connections/membrane-conn-1").status_code == 204

    email = client.post(
        "/api/v1/membrane/emails",
        json={
            "membrane_connection_id": "membrane-conn-1",
            "user_id": "user-1",
            "provider_message_id": "provider-message-new",
            "subject": "New",
        },
    )
    assert email.status_code == 201
    assert client.get("/api/v1/membrane/emails", params={"user_id": "user-1"}).json()["total"] == 1
    assert client.get("/api/v1/membrane/emails/membrane-email-1", params={"user_id": "user-1"}).json()["subject"] == "Membrane hello"
    assert client.get("/api/v1/membrane/emails/missing", params={"user_id": "user-1"}).status_code == 404

    event = client.post(
        "/api/v1/membrane/events",
        json={
            "membrane_connection_id": "membrane-conn-1",
            "user_id": "user-1",
            "provider_event_id": "provider-event-new",
            "subject": "New",
        },
    )
    assert event.status_code == 201
    assert client.get("/api/v1/membrane/events", params={"user_id": "user-1"}).json()["total"] == 1
    assert client.get("/api/v1/membrane/events/membrane-event-1", params={"user_id": "user-1"}).json()["subject"] == "Membrane demo"
    assert client.get("/api/v1/membrane/events/missing", params={"user_id": "user-1"}).status_code == 404


@pytest.mark.asyncio
async def test_publishers_emit_email_domain_events(monkeypatch):
    published = []

    async def fake_publish(event):
        published.append(event)

    monkeypatch.setattr(publishers.event_bus, "publish", fake_publish)
    await publishers.publish_email_received("email-1", {"subject": "Hello"})
    await publishers.publish_email_synced("email-1", {"count": 1})
    assert [event.event_type for event in published] == ["email.received", "email.synced"]
    assert [event.payload["entity_id"] for event in published] == ["email-1", "email-1"]


def test_database_facade_and_schema_contracts(monkeypatch):
    monkeypatch.setattr(database, "create_db_engine", lambda api_name: f"engine:{api_name}")
    monkeypatch.setattr(database, "create_session_factory", lambda api_name: f"factory:{api_name}")
    database.init("email-backend")
    assert database.get_engine() == "engine:email-backend"
    assert database.get_session_factory() == "factory:email-backend"

    assert ms365_schemas.ConnectionResponse.model_validate(make_connection()).id == "conn-1"
    assert ms365_schemas.EmailResponse.model_validate(make_email()).id == "email-1"
    assert ms365_schemas.EventResponse.model_validate(make_event()).id == "event-1"
    assert ms365_schemas.EmailContactLinkRequest(contact_id="contact-1").role == "from"
    assert smart_label_schemas.SmartLabelResponse.model_validate(make_smart_label()).name == "Priority"
    assert integration_settings_schemas.IntegrationSettingResponse.model_validate(make_integration()).integration_key == "microsoft-outlook"
    assert membrane_schemas.MembraneConnectionResponse.model_validate(make_membrane_connection()).id == "membrane-conn-1"
    assert membrane_schemas.MembraneEmailResponse.model_validate(make_membrane_email()).id == "membrane-email-1"
    assert membrane_schemas.MembraneEventResponse.model_validate(make_membrane_event()).id == "membrane-event-1"


def test_repository_methods_cover_persistence_paths():
    session = FakeDB()
    ms365 = MS365Repository(session)
    assert ms365.get_connection_by_user("user-1", "tenant-1").id == "conn-1"
    assert ms365.get_connection_by_id("conn-1", "tenant-1").id == "conn-1"
    assert ms365.get_all_active_connections()[0].id == "conn-1"
    assert ms365.update_connection(session.connection, {"ms_email": "updated@example.com"}).version == 2
    assert ms365.soft_delete_connection(session.connection, "admin@example.com").is_deleted is True
    assert ms365.upsert_email({"ms_message_id": "message-1", "subject": "Updated"}, "tenant-1").subject == "Updated"
    assert ms365.get_email_by_id("email-1", "user-1", "tenant-1").id == "email-1"
    assert len(ms365.list_emails("user-1", "tenant-1", folder="inbox", search="Hello", linked_contact_id="contact-1", smart_label="priority")) == 1
    assert ms365.count_emails("user-1", "tenant-1", folder="inbox", search="Hello", linked_contact_id="contact-1", smart_label="priority") == 1
    assert ms365.update_email(session.email, {"is_read": True}).is_read is True
    ms365.delete_email(session.email)
    assert ms365.upsert_event({"ms_event_id": "ms-event-1", "subject": "Updated"}, "tenant-1").subject == "Updated"
    assert ms365.get_event_by_id("event-1", "user-1", "tenant-1").id == "event-1"
    assert len(ms365.list_events("user-1", "tenant-1", from_date=NOW, to_date=NOW + timedelta(days=1))) == 1
    assert ms365.count_events("user-1", "tenant-1", from_date=NOW, to_date=NOW + timedelta(days=1)) == 1
    assert ms365.update_event(session.event, {"location": "Office"}).location == "Office"
    ms365.delete_event(session.event)
    ms365.link_email_contact("email-1", "contact-1", "from")
    ms365.unlink_email_contact("email-1", "contact-1")
    assert ms365.get_email_contacts("email-1")[0].contact_id == "contact-1"

    labels = SmartLabelRepository(session)
    assert labels.create(make_smart_label("label-new")).id == "label-new"
    assert labels.get_by_id("label-1", "tenant-1").id == "label-1"
    assert labels.get_by_name("Priority", "tenant-1").id == "label-1"
    assert labels.list_all("tenant-1")[0].id == "label-1"
    assert labels.count("tenant-1") == 2
    assert labels.update(session.label).version == 2
    labels.delete(session.label)

    settings_repo = IntegrationSettingsRepository(session)
    assert settings_repo.list_settings("tenant-1")[0].id == "setting-1"
    assert settings_repo.get_setting("tenant-1", "microsoft-outlook").id == "setting-1"
    assert settings_repo.upsert_setting("tenant-1", "microsoft-outlook", {"display_name": "Updated"}).display_name == "Updated"
    empty_settings = IntegrationSettingsRepository(EmptyDB())
    created = empty_settings.upsert_setting(
        "tenant-1",
        "microsoft-outlook",
        {"integration_key": "microsoft-outlook", "display_name": "Outlook"},
    )
    assert created.integration_key == "microsoft-outlook"
    assert settings_repo.delete_setting("tenant-1", "microsoft-outlook") is True
    assert IntegrationSettingsRepository(EmptyDB()).delete_setting("tenant-1", "missing") is False

    membrane = MembraneRepository(session)
    assert membrane.get_connection_by_membrane_id("membrane-provider-1", "tenant-1").id == "membrane-conn-1"
    assert membrane.get_connection_by_user_integration("user-1", "microsoft-outlook", "tenant-1").id == "membrane-conn-1"
    assert membrane.update_connection(session.membrane_connection, {"connection_name": "Updated"}).version == 2
    assert membrane.soft_delete_connection(session.membrane_connection, "admin").is_deleted is True
    assert membrane.upsert_email({"provider_message_id": "provider-message-1", "subject": "Updated"}, "tenant-1").subject == "Updated"
    assert membrane.get_email_by_id("membrane-email-1", "user-1", "tenant-1").id == "membrane-email-1"
    assert len(membrane.list_emails("user-1", "tenant-1", folder="inbox", search="hello")) == 1
    assert membrane.count_emails("user-1", "tenant-1", folder="inbox", search="hello") == 1
    assert membrane.upsert_event({"provider_event_id": "provider-event-1", "subject": "Updated"}, "tenant-1").subject == "Updated"
    assert membrane.get_event_by_id("membrane-event-1", "user-1", "tenant-1").id == "membrane-event-1"
    assert len(membrane.list_events("user-1", "tenant-1", from_date=NOW, to_date=NOW + timedelta(days=1))) == 1
    assert membrane.count_events("user-1", "tenant-1", from_date=NOW, to_date=NOW + timedelta(days=1)) == 1


def test_python_package_contract_loads_runtime_components():
    from email_backend_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (
        connection_routes,
        email_routes,
        event_routes,
        email_contact_routes,
        smart_label_routes,
        integration_settings_routes,
        membrane_routes,
        provider_ms365_routes,
        provider_membrane_routes,
    )
    assert contract.load_runtime_repository_classes() == (
        MS365Repository,
        SmartLabelRepository,
        IntegrationSettingsRepository,
        MembraneRepository,
    )
    assert contract.load_runtime_entity_classes() == (
        MS365Connection,
        SyncedEmail,
        SyncedEvent,
        SmartLabel,
        IntegrationSetting,
        MembraneConnection,
        MembraneSyncedEmail,
        MembraneSyncedEvent,
    )
