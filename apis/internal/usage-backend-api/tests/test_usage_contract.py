from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.infrastructure.persistence.models.usage_transaction import (
    BillingCategory,
    CostRateCard,
    RateUnitType,
    ServiceType,
    TriggerSource,
    UsageTransaction,
)
from app.events import publishers
from app.infrastructure import database
from app.infrastructure.persistence.usage_repository import UsageRepository
from app.middleware.auth import get_current_user, settings
from app.presentation import deps as usage_deps
from app.presentation.routes import usage_routes
from app.presentation.schemas import usage_schemas


USER = {"user_id": "user-1", "email": "user@example.com", "tenant_id": "tenant-1"}
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_txn(txn_id="txn-1", **overrides):
    txn = UsageTransaction(
        id=txn_id,
        tenant_id="tenant-1",
        user_id="user-1",
        user_email="user@example.com",
        service_type=ServiceType.LLM,
        provider="openai",
        model="gpt",
        is_billable=True,
        billing_category=BillingCategory.AI_USAGE,
        trigger_source=TriggerSource.BOB_CHAT,
        trigger_id="trigger-1",
        correlation_id="corr-1",
        correlation_label="Chat",
        input_tokens=10,
        output_tokens=20,
        audio_seconds=None,
        characters=None,
        voip_minutes=None,
        cogs_amount=0.123456,
        cogs_currency="USD",
        metadata_={"tool": "chat"},
        duration_ms=125.0,
    )
    txn.timestamp = NOW
    for key, value in overrides.items():
        setattr(txn, key, value)
    return txn


def make_rate_card(card_id="card-1", **overrides):
    card = CostRateCard(
        id=card_id,
        provider="openai",
        model="gpt",
        service_type=ServiceType.LLM,
        unit_type=RateUnitType.INPUT_TOKEN,
        rate_per_unit=0.000001,
        currency="USD",
        effective_from="2026-01-01",
        effective_to=None,
    )
    for key, value in overrides.items():
        setattr(card, key, value)
    return card


class FakeUsageRepository:
    def __init__(self, db):
        self.db = db
        self.transactions = {"txn-1": make_txn()}
        self.cards = {"card-1": make_rate_card()}

    def record(self, txn):
        txn.id = "txn-new"
        txn.timestamp = NOW
        self.transactions[txn.id] = txn
        return txn

    def list_by_tenant(self, tenant_id=None, skip=0, limit=50, **filters):
        items = list(self.transactions.values())
        if tenant_id:
            items = [txn for txn in items if txn.tenant_id == tenant_id]
        return items[skip : skip + limit]

    def count_by_tenant(self, tenant_id=None, **filters):
        return len(self.list_by_tenant(tenant_id, **filters))

    def get_summary(self, tenant_id, date_from=None, date_to=None):
        return [{
            "service_type": "LLM",
            "billing_category": "AI_USAGE",
            "transaction_count": 2,
            "total_cogs": 0.25,
            "total_input_tokens": 10,
            "total_output_tokens": 20,
        }]

    def list_by_correlation(self, tenant_id=None, skip=0, limit=50):
        return [{
            "correlation_id": "corr-1",
            "correlation_label": "Chat",
            "transaction_count": 2,
            "total_cogs": 0.25,
            "first_at": "2026-01-01T00:00:00+00:00",
            "last_at": "2026-01-01T00:00:00+00:00",
        }]

    def count_by_correlation(self, tenant_id=None):
        return 1

    def sum_cogs_by_correlation(self, tenant_id=None):
        return 0.25

    def list_by_correlation_id(self, correlation_id):
        return [txn for txn in self.transactions.values() if txn.correlation_id == correlation_id]

    def list_rate_cards(self, active_only=True):
        return list(self.cards.values())

    def create_rate_card(self, card):
        card.id = "card-new"
        card.effective_from = "2026-01-01"
        card.effective_to = None
        self.cards[card.id] = card
        return card

    def get_rate_card(self, card_id):
        return self.cards.get(card_id)


class FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.refreshed = []

    def add(self, entity):
        self.added.append(entity)

    def commit(self):
        self.commits += 1

    def refresh(self, entity):
        self.refreshed.append(entity)


class FakeQuery:
    def __init__(self, result=None, results=None, count_value=1, scalar_value=1):
        self.result = result
        self.results = list(results or [])
        self.count_value = count_value
        self.scalar_value = scalar_value

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def offset(self, skip):
        self.results = self.results[skip:]
        return self

    def limit(self, limit):
        self.results = self.results[:limit]
        return self

    def group_by(self, *args):
        return self

    def first(self):
        return self.result

    def all(self):
        return self.results

    def count(self):
        return self.count_value

    def scalar(self):
        return self.scalar_value


class RepositorySession(FakeDB):
    def __init__(self):
        super().__init__()
        self.txn = make_txn()
        self.card = make_rate_card()
        self.summary_row = SimpleNamespace(
            service_type=ServiceType.LLM,
            billing_category=BillingCategory.AI_USAGE,
            transaction_count=2,
            total_cogs=0.25,
            total_input_tokens=10,
            total_output_tokens=20,
        )
        self.correlation_row = SimpleNamespace(
            correlation_id="corr-1",
            correlation_label="Chat",
            transaction_count=2,
            total_cogs=0.25,
            first_at=NOW,
            last_at=NOW,
        )

    def query(self, *entities):
        first = entities[0] if entities else None
        key = getattr(first, "key", "")
        if first is UsageTransaction:
            return FakeQuery(self.txn, [self.txn], 1)
        if first is CostRateCard:
            return FakeQuery(self.card, [self.card], 1)
        if key == "service_type":
            return FakeQuery(results=[self.summary_row])
        if key == "correlation_id":
            return FakeQuery(results=[self.correlation_row])
        return FakeQuery(scalar_value=1)


@pytest.fixture()
def repo():
    return FakeUsageRepository(FakeDB())


@pytest.fixture()
def client(monkeypatch, repo):
    async def noop_publish(*args, **kwargs):
        return None

    monkeypatch.setattr(usage_deps, "UsageRepository", lambda db: repo)
    monkeypatch.setattr(usage_deps, "publish_usage_recorded", noop_publish)
    main.app.dependency_overrides[usage_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[usage_deps.get_db] = lambda: FakeDB()
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers():
    token = jwt.encode(
        {"sub": "user-1", "email": "user@example.com", "tenant_id": "tenant-1"},
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


def test_usage_routes(client):
    created = client.post(
        "/api/v1/usage",
        json={
            "service_type": "LLM",
            "billing_category": "AI_USAGE",
            "trigger_source": "BOB_CHAT",
            "provider": "openai",
            "model": "gpt",
            "input_tokens": 10,
            "output_tokens": 20,
            "cogs_amount": 0.123456,
            "correlation_id": "corr-1",
            "metadata": {"tool": "chat"},
        },
    )
    assert created.status_code == 201
    assert created.json()["id"] == "txn-new"

    listed = client.get("/api/v1/usage", params={"service_type": "LLM", "billing_category": "AI_USAGE"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    summary = client.get("/api/v1/usage/summary").json()
    assert summary["total_transactions"] == 2
    assert summary["total_cogs"] == 0.25

    admin_list = client.get("/api/v1/admin/usage", params={"tenant_id": "tenant-1"}).json()
    assert admin_list["items"][0]["id"] == "txn-1"
    admin_summary = client.get("/api/v1/admin/usage/summary", params={"tenant_id": "tenant-1"}).json()
    assert admin_summary["tenant_id"] == "tenant-1"

    by_intent = client.get("/api/v1/admin/usage/by-intent", params={"tenant_id": "tenant-1"}).json()
    assert by_intent["items"][0]["correlation_id"] == "corr-1"
    detail = client.get("/api/v1/admin/usage/by-intent/corr-1").json()
    assert detail["total"] >= 1


def test_rate_card_routes(client):
    listed = client.get("/api/v1/rate-cards")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == "card-1"

    created = client.post(
        "/api/v1/rate-cards",
        json={
            "provider": "openai",
            "model": "gpt",
            "service_type": "LLM",
            "unit_type": "INPUT_TOKEN",
            "rate_per_unit": 0.000001,
        },
    )
    assert created.status_code == 201
    assert created.json()["id"] == "card-new"


def test_auth_dependency_accepts_and_rejects_tokens(auth_headers):
    credentials = type("Credentials", (), {"credentials": auth_headers["Authorization"].split(" ", 1)[1]})()
    assert get_current_user(credentials)["tenant_id"] == "tenant-1"

    invalid = type("Credentials", (), {"credentials": "not-a-token"})()
    with pytest.raises(Exception) as invalid_token:
        get_current_user(invalid)
    assert getattr(invalid_token.value, "status_code", None) == 401

    no_sub = jwt.encode({"email": "user@example.com"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(Exception) as missing_sub:
        get_current_user(type("Credentials", (), {"credentials": no_sub})())
    assert getattr(missing_sub.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_publishers_emit_usage_event(monkeypatch):
    published = []

    async def fake_publish(event):
        published.append(event)

    monkeypatch.setattr(publishers.event_bus, "publish", fake_publish)
    await publishers.publish_usage_recorded("txn-1", {"service_type": "LLM"})
    assert published == [{"type": "usage.recorded", "transaction_id": "txn-1", "data": {"service_type": "LLM"}}]


def test_repository_methods_cover_persistence_paths():
    session = RepositorySession()
    repository = UsageRepository(session)

    assert repository.record(make_txn("txn-new")).id == "txn-new"
    assert repository.list_by_tenant("tenant-1", service_type="LLM", billing_category="AI_USAGE")[0].id == "txn-1"
    assert repository.count_by_tenant("tenant-1", user_id="user-1") == 1
    assert repository.get_summary("tenant-1")[0]["service_type"] == "LLM"
    assert repository.list_by_correlation("tenant-1")[0]["correlation_id"] == "corr-1"
    assert repository.count_by_correlation("tenant-1") == 1
    assert repository.sum_cogs_by_correlation("tenant-1") == 1.0
    assert repository.list_by_correlation_id("corr-1")[0].id == "txn-1"
    assert repository.create_rate_card(make_rate_card("card-new")).id == "card-new"
    assert repository.list_rate_cards()[0].id == "card-1"
    assert repository.list_rate_cards(active_only=False)[0].id == "card-1"
    assert repository.get_rate_card("card-1").id == "card-1"
    assert session.commits >= 1


def test_database_facade_and_schema_contracts(monkeypatch):
    monkeypatch.setattr(database, "create_db_engine", lambda api_name: f"engine:{api_name}")
    monkeypatch.setattr(database, "create_session_factory", lambda api_name: f"factory:{api_name}")
    database.init("usage-backend")
    assert database.get_engine() == "engine:usage-backend"
    assert database.get_session_factory() == "factory:usage-backend"

    assert usage_schemas.UsageTransactionCreate(
        service_type="LLM",
        billing_category="AI_USAGE",
        trigger_source="BOB_CHAT",
    ).is_billable is True
    assert usage_schemas.UsageTransactionResponse.model_validate(make_txn()).id == "txn-1"
    item = usage_schemas.UsageSummaryItem(service_type="LLM", transaction_count=1)
    assert usage_schemas.UsageSummaryResponse(tenant_id="tenant-1", items=[item]).total_cogs == 0.0
    group = usage_schemas.UsageCorrelationGroupResponse(correlation_id="corr-1")
    assert usage_schemas.UsageCorrelationListResponse(items=[group], total=1).total == 1
    assert usage_schemas.RateCardCreate(
        provider="openai",
        model="gpt",
        service_type="LLM",
        unit_type="INPUT_TOKEN",
        rate_per_unit=0.000001,
    ).currency == "USD"
    assert usage_schemas.RateCardResponse.model_validate(make_rate_card()).id == "card-1"


def test_python_package_contract_loads_runtime_components():
    from usage_backend_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (usage_routes,)
    assert contract.load_runtime_repository_classes() == (UsageRepository,)
    assert contract.load_runtime_entity_classes() == (
        UsageTransaction,
        CostRateCard,
        ServiceType,
        BillingCategory,
        TriggerSource,
        RateUnitType,
    )
