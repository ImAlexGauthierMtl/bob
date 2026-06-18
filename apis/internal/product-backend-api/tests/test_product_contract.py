from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.domain.entities.product import BillingCycle, BillingUnit, LicenseType, Product, ProductCategory
from app.events import publishers
from app.infrastructure import database
from app.infrastructure.persistence.product_repository import ProductRepository
from app.middleware.auth import get_current_user, settings
from app.presentation.routes import product_routes
from app.presentation.schemas import product_schemas


USER = {"user_id": "user-1", "email": "user@example.com", "tenant_id": "tenant-1"}
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_product(product_id="prod-1", **overrides):
    product = Product(
        id=product_id,
        name="Product",
        description="Useful product",
        category=ProductCategory.SOFTWARE,
        unit_price=100.0,
        currency="CAD",
        sku="SKU-001",
        is_active=True,
        is_taxable=True,
        tax_rate=0.05,
        billing_cycle=BillingCycle.MONTHLY,
        contract_term_months=12,
        setup_fee=10.0,
        tenant_id="tenant-1",
        created_by="user@example.com",
        updated_by=None,
    )
    product.created_at = NOW
    product.updated_at = NOW
    product.version = 1
    product.is_deleted = False
    product.deleted_at = None
    product.deleted_by = None
    for key, value in overrides.items():
        setattr(product, key, value)
    return product


class FakeProductRepository:
    def __init__(self, db):
        self.db = db
        self.products = {"prod-1": make_product()}

    def create(self, product):
        product.id = "prod-new"
        product.created_at = NOW
        product.updated_at = NOW
        product.version = 1
        product.is_active = True
        product.is_deleted = False
        self.products[product.id] = product
        return product

    def get_by_id(self, product_id, tenant_id):
        product = self.products.get(product_id)
        return product if product and product.tenant_id == tenant_id and not product.is_deleted else None

    def list_all(self, tenant_id, skip=0, limit=50, category=None, active_only=True):
        items = [p for p in self.products.values() if p.tenant_id == tenant_id and not p.is_deleted]
        if active_only:
            items = [p for p in items if p.is_active]
        if category:
            items = [p for p in items if p.category == category or getattr(p.category, "value", p.category) == category]
        return items[skip : skip + limit]

    def count(self, tenant_id, active_only=True):
        return len(self.list_all(tenant_id, active_only=active_only))

    def update(self, product):
        product.updated_at = NOW
        product.version = (product.version or 0) + 1
        return product

    def soft_delete(self, product, deleted_by):
        product.is_deleted = True
        product.deleted_at = NOW
        product.deleted_by = deleted_by
        product.version = (product.version or 0) + 1
        return product


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
        self.product = make_product()

    def query(self, entity):
        if entity is Product:
            return FakeQuery(self.product, [self.product], 1)
        return FakeQuery()


@pytest.fixture()
def repo():
    return FakeProductRepository(FakeDB())


@pytest.fixture()
def client(monkeypatch, repo):
    async def noop_publish(*args, **kwargs):
        return None

    monkeypatch.setattr(product_routes, "ProductRepository", lambda db: repo)
    monkeypatch.setattr(product_routes, "publish_product_created", noop_publish)
    monkeypatch.setattr(product_routes, "publish_product_updated", noop_publish)
    main.app.dependency_overrides[product_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[product_routes.get_db] = lambda: FakeDB()
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


def test_product_crud_routes(client):
    created = client.post(
        "/api/v1/products",
        json={
            "name": "New product",
            "description": "Created through the route",
            "category": "SERVICE",
            "unit_price": 42.5,
        },
    )
    assert created.status_code == 201
    assert created.json()["id"] == "prod-new"

    listed = client.get("/api/v1/products", params={"category": "SOFTWARE"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert client.get("/api/v1/products/prod-1").json()["id"] == "prod-1"
    assert client.get("/api/v1/products/missing").status_code == 404
    assert client.patch("/api/v1/products/prod-1", json={"name": "Updated"}).json()["name"] == "Updated"
    assert client.patch("/api/v1/products/missing", json={"name": "Updated"}).status_code == 404
    assert client.delete("/api/v1/products/prod-1").status_code == 204
    assert client.delete("/api/v1/products/missing").status_code == 404


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
    await publishers.publish_product_created("prod-1", {"name": "Product"})
    await publishers.publish_product_updated("prod-1", {"name": "Updated"})
    assert [event.event_type for event in published] == ["product.created", "product.updated"]
    assert [event.payload["entity_id"] for event in published] == ["prod-1", "prod-1"]


def test_repository_methods_cover_persistence_paths():
    session = RepositorySession()
    repository = ProductRepository(session)

    assert repository.create(make_product("prod-new")).id == "prod-new"
    assert repository.get_by_id("prod-1", "tenant-1").id == "prod-1"
    assert repository.list_all("tenant-1", category="SOFTWARE")[0].id == "prod-1"
    assert repository.count("tenant-1") == 1
    assert repository.update(session.product).version == 2
    assert repository.soft_delete(session.product, "user@example.com").is_deleted is True
    assert session.commits >= 1


def test_database_facade_and_schema_contracts(monkeypatch):
    monkeypatch.setattr(database, "create_db_engine", lambda api_name: f"engine:{api_name}")
    monkeypatch.setattr(database, "create_session_factory", lambda api_name: f"factory:{api_name}")
    database.init("product-backend")
    assert database.get_engine() == "engine:product-backend"
    assert database.get_session_factory() == "factory:product-backend"

    assert product_schemas.ProductCreate(name="Product").currency == "CAD"
    assert product_schemas.ProductUpdate(name="Updated").name == "Updated"
    response = product_schemas.ProductResponse.model_validate(make_product())
    assert response.id == "prod-1"
    assert product_schemas.ProductListResponse(items=[response], total=1, skip=0, limit=50).total == 1


def test_python_package_contract_loads_runtime_components():
    from product_backend_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (product_routes,)
    assert contract.load_runtime_repository_classes() == (ProductRepository,)
    assert contract.load_runtime_entity_classes() == (
        Product,
        ProductCategory,
        BillingCycle,
        LicenseType,
        BillingUnit,
    )
