from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.infrastructure.persistence.models.opportunity import Opportunity, OpportunityPriority, OpportunityStage
from app.infrastructure.persistence.models.opportunity_product import OpportunityProduct
from app.infrastructure.persistence.models.quote import Quote, QuoteStatus
from app.events import publishers
from app.infrastructure import database
from app.infrastructure.persistence.opportunity_repository import OpportunityRepository
from app.infrastructure.persistence.quote_repository import QuoteRepository
from app.middleware.auth import get_current_user, settings
from app.presentation import deps as opportunity_deps
from app.presentation.routes import opportunity_routes, quote_routes
from app.presentation.schemas import opportunity_schemas, quote_schemas


USER = {"user_id": "user-1", "email": "user@example.com", "tenant_id": "tenant-1"}
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
TODAY = date(2026, 1, 31)


def make_opportunity(opp_id="opp-1", **overrides):
    opp = Opportunity(
        id=opp_id,
        name="Opportunity",
        description="Potential deal",
        stage=OpportunityStage.PROSPECTING,
        priority=OpportunityPriority.MEDIUM,
        amount=10000.0,
        probability=0.5,
        close_date=TODAY,
        source="referral",
        organization_id="org-1",
        contact_id="contact-1",
        owner_id="user-1",
        tenant_id="tenant-1",
        created_by="user@example.com",
        updated_by=None,
    )
    opp.created_at = NOW
    opp.updated_at = NOW
    opp.version = 1
    opp.is_deleted = False
    opp.deleted_at = None
    opp.deleted_by = None
    opp.deleted_reason = None
    for key, value in overrides.items():
        setattr(opp, key, value)
    return opp


def make_line(line_id="line-1", **overrides):
    line = OpportunityProduct(
        id=line_id,
        opportunity_id="opp-1",
        product_id="prod-1",
        quantity=2,
        unit_price=125.0,
        discount_percent=10.0,
        notes="Line notes",
        tenant_id="tenant-1",
        created_by="user@example.com",
        updated_by=None,
    )
    line.created_at = NOW
    line.updated_at = NOW
    line.version = 1
    for key, value in overrides.items():
        setattr(line, key, value)
    return line


def make_quote(quote_id="quote-1", **overrides):
    quote = Quote(
        id=quote_id,
        name="Quote",
        description="Commercial quote",
        status=QuoteStatus.DRAFT,
        subtotal=1000.0,
        discount_percent=5.0,
        tax_percent=14.975,
        total=1092.26,
        valid_until=TODAY,
        terms="Net 30",
        notes="Quote notes",
        opportunity_id="opp-1",
        organization_id="org-1",
        owner_id="user-1",
        tenant_id="tenant-1",
        created_by="user@example.com",
        updated_by=None,
    )
    quote.created_at = NOW
    quote.updated_at = NOW
    quote.version = 1
    quote.is_deleted = False
    quote.deleted_at = None
    quote.deleted_by = None
    quote.deleted_reason = None
    for key, value in overrides.items():
        setattr(quote, key, value)
    return quote


class FakeOpportunityRepository:
    def __init__(self, db):
        self.db = db
        self.opportunities = {"opp-1": make_opportunity()}
        self.lines = {"line-1": make_line()}

    def create(self, opp):
        opp.id = "opp-new"
        opp.created_at = NOW
        opp.updated_at = NOW
        opp.version = 1
        opp.is_deleted = False
        self.opportunities[opp.id] = opp
        return opp

    def get_by_id(self, opp_id, tenant_id):
        opp = self.opportunities.get(opp_id)
        return opp if opp and opp.tenant_id == tenant_id and not opp.is_deleted else None

    def list_all(self, tenant_id, skip=0, limit=50, organization_id=None, stage=None):
        items = [o for o in self.opportunities.values() if o.tenant_id == tenant_id and not o.is_deleted]
        if organization_id:
            items = [o for o in items if o.organization_id == organization_id]
        if stage:
            items = [o for o in items if o.stage == stage or getattr(o.stage, "value", o.stage) == stage]
        return items[skip : skip + limit]

    def count(self, tenant_id, organization_id=None):
        return len(self.list_all(tenant_id, organization_id=organization_id))

    def update(self, opp):
        opp.updated_at = NOW
        opp.version = (opp.version or 0) + 1
        return opp

    def soft_delete(self, opp, deleted_by, reason=None):
        opp.is_deleted = True
        opp.deleted_at = NOW
        opp.deleted_by = deleted_by
        opp.deleted_reason = reason
        opp.version = (opp.version or 0) + 1
        return opp

    def add_product(self, line):
        line.id = "line-new"
        line.created_at = NOW
        line.updated_at = NOW
        line.version = 1
        self.lines[line.id] = line
        return line

    def list_products(self, opp_id, tenant_id):
        return [line for line in self.lines.values() if line.opportunity_id == opp_id and line.tenant_id == tenant_id]

    def get_product_line(self, line_id, tenant_id):
        line = self.lines.get(line_id)
        return line if line and line.tenant_id == tenant_id else None

    def remove_product(self, line):
        self.lines.pop(line.id, None)


class FakeQuoteRepository:
    def __init__(self, db):
        self.db = db
        self.quotes = {"quote-1": make_quote()}

    def create(self, quote):
        quote.id = "quote-new"
        quote.created_at = NOW
        quote.updated_at = NOW
        quote.version = 1
        quote.is_deleted = False
        self.quotes[quote.id] = quote
        return quote

    def get_by_id(self, quote_id, tenant_id):
        quote = self.quotes.get(quote_id)
        return quote if quote and quote.tenant_id == tenant_id and not quote.is_deleted else None

    def list_all(self, tenant_id, skip=0, limit=50, opportunity_id=None):
        items = [q for q in self.quotes.values() if q.tenant_id == tenant_id and not q.is_deleted]
        if opportunity_id:
            items = [q for q in items if q.opportunity_id == opportunity_id]
        return items[skip : skip + limit]

    def count(self, tenant_id):
        return len(self.list_all(tenant_id))

    def update(self, quote):
        quote.updated_at = NOW
        quote.version = (quote.version or 0) + 1
        return quote

    def soft_delete(self, quote, deleted_by, reason=None):
        quote.is_deleted = True
        quote.deleted_at = NOW
        quote.deleted_by = deleted_by
        quote.deleted_reason = reason
        quote.version = (quote.version or 0) + 1
        return quote


class FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.refreshed = []
        self.deleted = []

    def add(self, entity):
        self.added.append(entity)

    def commit(self):
        self.commits += 1

    def refresh(self, entity):
        self.refreshed.append(entity)

    def delete(self, entity):
        self.deleted.append(entity)


class FakeQuery:
    def __init__(self, result=None, results=None, count_value=1):
        self.result = result
        self.results = list(results or [])
        self.count_value = count_value

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

    def first(self):
        return self.result

    def all(self):
        return self.results

    def count(self):
        return self.count_value


class RepositorySession(FakeDB):
    def __init__(self):
        super().__init__()
        self.opportunity = make_opportunity()
        self.line = make_line()
        self.quote = make_quote()

    def query(self, entity):
        if entity is Opportunity:
            return FakeQuery(self.opportunity, [self.opportunity], 1)
        if entity is OpportunityProduct:
            return FakeQuery(self.line, [self.line], 1)
        if entity is Quote:
            return FakeQuery(self.quote, [self.quote], 1)
        return FakeQuery()


@pytest.fixture()
def repos():
    db = FakeDB()
    return FakeOpportunityRepository(db), FakeQuoteRepository(db)


@pytest.fixture()
def client(monkeypatch, repos):
    opp_repo, quote_repo = repos

    async def noop_publish(*args, **kwargs):
        return None

    monkeypatch.setattr(opportunity_deps, "OpportunityRepository", lambda db: opp_repo)
    monkeypatch.setattr(opportunity_deps, "QuoteRepository", lambda db: quote_repo)
    monkeypatch.setattr(opportunity_deps, "publish_opportunity_created", noop_publish)
    monkeypatch.setattr(opportunity_deps, "publish_opportunity_updated", noop_publish)
    main.app.dependency_overrides[opportunity_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[opportunity_deps.get_db] = lambda: FakeDB()
    main.app.dependency_overrides[quote_routes.get_current_user] = lambda: USER
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


def test_opportunity_crud_routes(client):
    created = client.post(
        "/api/v1/opportunities",
        json={"name": "New deal", "organization_id": "org-1", "stage": "QUALIFICATION"},
    )
    assert created.status_code == 201
    assert created.json()["id"] == "opp-new"

    listed = client.get("/api/v1/opportunities", params={"organization_id": "org-1", "stage": "PROSPECTING"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert client.get("/api/v1/opportunities/opp-1").json()["id"] == "opp-1"
    assert client.get("/api/v1/opportunities/missing").status_code == 404
    assert client.patch("/api/v1/opportunities/opp-1", json={"name": "Updated"}).json()["name"] == "Updated"
    assert client.patch("/api/v1/opportunities/missing", json={"name": "Updated"}).status_code == 404
    assert client.delete("/api/v1/opportunities/opp-1").status_code == 204
    assert client.delete("/api/v1/opportunities/missing").status_code == 404


def test_opportunity_product_routes(client):
    listed = client.get("/api/v1/opportunities/opp-1/products")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == "line-1"

    created = client.post(
        "/api/v1/opportunities/opp-1/products",
        json={"product_id": "prod-2", "quantity": 3, "unit_price": 200.0},
    )
    assert created.status_code == 201
    assert created.json()["id"] == "line-new"
    assert client.post(
        "/api/v1/opportunities/missing/products",
        json={"product_id": "prod-2", "quantity": 3, "unit_price": 200.0},
    ).status_code == 404
    assert client.delete("/api/v1/opportunities/opp-1/products/line-1").status_code == 204
    assert client.delete("/api/v1/opportunities/opp-1/products/missing").status_code == 404


def test_quote_crud_routes(client):
    created = client.post(
        "/api/v1/quotes",
        json={"name": "New quote", "opportunity_id": "opp-1", "organization_id": "org-1"},
    )
    assert created.status_code == 201
    assert created.json()["id"] == "quote-new"

    listed = client.get("/api/v1/quotes", params={"opportunity_id": "opp-1"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert client.get("/api/v1/quotes/quote-1").json()["id"] == "quote-1"
    assert client.get("/api/v1/quotes/missing").status_code == 404
    assert client.patch("/api/v1/quotes/quote-1", json={"name": "Updated"}).json()["name"] == "Updated"
    assert client.patch("/api/v1/quotes/missing", json={"name": "Updated"}).status_code == 404
    assert client.delete("/api/v1/quotes/quote-1").status_code == 204
    assert client.delete("/api/v1/quotes/missing").status_code == 404


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
async def test_publishers_emit_domain_events(monkeypatch):
    published = []

    async def fake_publish(event):
        published.append(event)

    monkeypatch.setattr(publishers.event_bus, "publish", fake_publish)
    await publishers.publish_opportunity_created("opp-1", {"name": "Opportunity"})
    await publishers.publish_opportunity_updated("opp-1", {"name": "Updated"})
    assert [event.event_type for event in published] == ["opportunity.created", "opportunity.updated"]
    assert [event.payload["entity_id"] for event in published] == ["opp-1", "opp-1"]


def test_repository_methods_cover_persistence_paths():
    session = RepositorySession()
    opp_repository = OpportunityRepository(session)
    quote_repository = QuoteRepository(session)

    assert opp_repository.create(make_opportunity("opp-new")).id == "opp-new"
    assert opp_repository.get_by_id("opp-1", "tenant-1").id == "opp-1"
    assert opp_repository.list_all("tenant-1", organization_id="org-1", stage="PROSPECTING")[0].id == "opp-1"
    assert opp_repository.count("tenant-1", organization_id="org-1") == 1
    assert opp_repository.update(session.opportunity).version == 2
    deleted_opp = opp_repository.soft_delete(session.opportunity, "user@example.com", reason="duplicate")
    assert deleted_opp.is_deleted is True
    assert deleted_opp.deleted_reason == "duplicate"
    assert opp_repository.add_product(make_line("line-new")).id == "line-new"
    assert opp_repository.list_products("opp-1", "tenant-1")[0].id == "line-1"
    assert opp_repository.get_product_line("line-1", "tenant-1").id == "line-1"
    opp_repository.remove_product(session.line)
    assert session.deleted == [session.line]

    assert quote_repository.create(make_quote("quote-new")).id == "quote-new"
    assert quote_repository.get_by_id("quote-1", "tenant-1").id == "quote-1"
    assert quote_repository.list_all("tenant-1", opportunity_id="opp-1")[0].id == "quote-1"
    assert quote_repository.count("tenant-1") == 1
    assert quote_repository.update(session.quote).version == 2
    deleted_quote = quote_repository.soft_delete(session.quote, "user@example.com", reason="expired")
    assert deleted_quote.is_deleted is True
    assert deleted_quote.deleted_reason == "expired"
    assert session.commits >= 1


def test_database_facade_and_schema_contracts(monkeypatch):
    monkeypatch.setattr(database, "create_db_engine", lambda api_name: f"engine:{api_name}")
    monkeypatch.setattr(database, "create_session_factory", lambda api_name: f"factory:{api_name}")
    database.init("opportunity-backend")
    assert database.get_engine() == "engine:opportunity-backend"
    assert database.get_session_factory() == "factory:opportunity-backend"

    assert opportunity_schemas.OpportunityCreate(name="Deal").stage == "PROSPECTING"
    assert opportunity_schemas.OpportunityUpdate(name="Updated").name == "Updated"
    opp_response = opportunity_schemas.OpportunityResponse.model_validate(make_opportunity())
    assert opp_response.id == "opp-1"
    assert opportunity_schemas.OpportunityListResponse(items=[opp_response], total=1, skip=0, limit=50).total == 1
    assert opportunity_schemas.OpportunityProductCreate(product_id="prod-1", unit_price=1).quantity == 1
    assert opportunity_schemas.OpportunityProductResponse.model_validate(make_line()).id == "line-1"

    assert quote_schemas.QuoteCreate(name="Quote").status == "DRAFT"
    assert quote_schemas.QuoteUpdate(name="Updated").name == "Updated"
    quote_response = quote_schemas.QuoteResponse.model_validate(make_quote())
    assert quote_response.id == "quote-1"
    assert quote_schemas.QuoteListResponse(items=[quote_response], total=1, skip=0, limit=50).total == 1


def test_python_package_contract_loads_runtime_components():
    from opportunity_backend_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (opportunity_routes, quote_routes)
    assert contract.load_runtime_repository_classes() == (OpportunityRepository, QuoteRepository)
    assert contract.load_runtime_entity_classes() == (
        Opportunity,
        OpportunityStage,
        OpportunityPriority,
        OpportunityProduct,
        Quote,
        QuoteStatus,
    )
