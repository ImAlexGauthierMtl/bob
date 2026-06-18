from jose import jwt
import pytest
from fastapi.testclient import TestClient

import main
from app.infrastructure.clients.crm_clients import (
    ActivityClient,
    ContactClient,
    OpportunityClient,
    OrgClient,
    ProductClient,
)
from app.middleware.auth import get_current_user, settings
from app.presentation.schemas import crm_schemas
from app.presentation.routes import (
    activity_routes,
    contact_routes,
    department_routes,
    opportunity_routes,
    organization_routes,
    product_routes,
    quote_routes,
)


def entity_payload(kind, entity_id=None, **overrides):
    payload = {
        "id": entity_id or f"{kind}-1",
        "kind": kind,
        "name": f"{kind.title()} One",
        "status": "ACTIVE",
    }
    payload.update(overrides)
    return payload


class FakeCRMClient:
    def __init__(self, kind):
        self.kind = kind

    async def list(self, *args, **kwargs):
        skip = args[0] if len(args) > 0 else kwargs.get("skip", 0)
        limit = args[1] if len(args) > 1 else kwargs.get("limit", 50)
        return {"items": [entity_payload(self.kind)], "total": 1, "skip": skip, "limit": limit}

    async def get(self, entity_id, forward_headers=None):
        if entity_id == "missing":
            return None
        return entity_payload(self.kind, entity_id)

    async def create(self, data, forward_headers=None):
        return entity_payload(self.kind, f"{self.kind}-new", **data)

    async def update(self, entity_id, data, forward_headers=None):
        return entity_payload(self.kind, entity_id, **data)

    async def delete(self, entity_id, forward_headers=None):
        return entity_id != "missing"

    async def list_departments(self, forward_headers=None):
        return {"items": [entity_payload("department")], "total": 1}

    async def create_department(self, data, forward_headers=None):
        return entity_payload("department", "department-new", **data)

    async def get_department(self, dept_id, forward_headers=None):
        if dept_id == "missing":
            return None
        return entity_payload("department", dept_id)

    async def update_department(self, dept_id, data, forward_headers=None):
        return entity_payload("department", dept_id, **data)

    async def delete_department(self, dept_id, forward_headers=None):
        return dept_id != "missing"

    async def list_products(self, opp_id, forward_headers=None):
        return [entity_payload("opportunity-product", "line-1", opportunity_id=opp_id)]

    async def add_product(self, opp_id, data, forward_headers=None):
        return entity_payload("opportunity-product", "line-new", opportunity_id=opp_id, **data)

    async def remove_product(self, opp_id, line_id, forward_headers=None):
        return line_id != "missing"

    async def list_quotes(self, *args, **kwargs):
        skip = args[0] if len(args) > 0 else kwargs.get("skip", 0)
        limit = args[1] if len(args) > 1 else kwargs.get("limit", 50)
        return {"items": [entity_payload("quote")], "total": 1, "skip": skip, "limit": limit}

    async def create_quote(self, data, forward_headers=None):
        return entity_payload("quote", "quote-new", **data)

    async def get_quote(self, quote_id, forward_headers=None):
        if quote_id == "missing":
            return None
        return entity_payload("quote", quote_id)

    async def update_quote(self, quote_id, data, forward_headers=None):
        return entity_payload("quote", quote_id, **data)

    async def delete_quote(self, quote_id, forward_headers=None):
        return quote_id != "missing"


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload or {}
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class FakeServiceClient:
    def __init__(self, service_name):
        self.service_name = service_name
        self.calls = []

    def _kind_for_path(self, path):
        if "/contacts" in path:
            return "contact"
        if "/organizations" in path:
            return "organization"
        if "/opportunities" in path:
            return "opportunity-product" if "/products" in path else "opportunity"
        if "/quotes" in path:
            return "quote"
        if "/activities" in path:
            return "activity"
        if "/products" in path:
            return "product"
        if "/departments" in path:
            return "department"
        return "crm"

    async def get(self, path, params=None, forward_headers=None):
        self.calls.append(("get", path, params, forward_headers))
        if path.endswith("/missing"):
            return FakeResponse(status_code=404)
        kind = self._kind_for_path(path)
        if path.count("/") <= 3 or path.endswith("/products") or path.endswith("/quotes") or path.endswith("/departments"):
            return FakeResponse({"items": [entity_payload(kind)], "total": 1, "skip": int((params or {}).get("skip", 0)), "limit": int((params or {}).get("limit", 50))})
        return FakeResponse(entity_payload(kind, path.rsplit("/", 1)[-1]))

    async def post(self, path, json=None, forward_headers=None):
        self.calls.append(("post", path, json, forward_headers))
        return FakeResponse(entity_payload(self._kind_for_path(path), f"{self._kind_for_path(path)}-new", **(json or {})), status_code=201)

    async def patch(self, path, json=None, forward_headers=None):
        self.calls.append(("patch", path, json, forward_headers))
        return FakeResponse(entity_payload(self._kind_for_path(path), path.rsplit("/", 1)[-1], **(json or {})))

    async def delete(self, path, forward_headers=None):
        self.calls.append(("delete", path, None, forward_headers))
        return FakeResponse(status_code=404 if path.endswith("/missing") else 204)


@pytest.fixture()
def client(monkeypatch):
    contact = FakeCRMClient("contact")
    org = FakeCRMClient("organization")
    opportunity = FakeCRMClient("opportunity")
    activity = FakeCRMClient("activity")
    product = FakeCRMClient("product")

    monkeypatch.setattr(contact_routes, "contact_client", contact)
    monkeypatch.setattr(organization_routes, "org_client", org)
    monkeypatch.setattr(department_routes, "org_client", org)
    monkeypatch.setattr(opportunity_routes, "opportunity_client", opportunity)
    monkeypatch.setattr(quote_routes, "opportunity_client", opportunity)
    monkeypatch.setattr(activity_routes, "activity_client", activity)
    monkeypatch.setattr(product_routes, "product_client", product)

    with TestClient(main.app) as test_client:
        yield test_client


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


def test_contact_routes(client, auth_headers):
    listed = client.get("/contacts", params={"skip": 1, "limit": 2, "search": "ada"}, headers=auth_headers)
    assert listed.json()["skip"] == 1
    assert client.post("/contacts", json={"name": "Ada"}, headers=auth_headers).status_code == 201
    assert client.get("/contacts/contact-1", headers=auth_headers).json()["id"] == "contact-1"
    assert client.get("/contacts/missing", headers=auth_headers).status_code == 404
    assert client.patch("/contacts/contact-1", json={"status": "INACTIVE"}, headers=auth_headers).json()["status"] == "INACTIVE"
    assert client.delete("/contacts/contact-1", headers=auth_headers).status_code == 204


def test_organization_and_department_routes(client, auth_headers):
    assert client.get("/organizations", params={"search": "croo"}, headers=auth_headers).json()["items"][0]["kind"] == "organization"
    assert client.post("/organizations", json={"name": "Croo"}, headers=auth_headers).status_code == 201
    assert client.get("/organizations/org-1", headers=auth_headers).json()["id"] == "org-1"
    assert client.get("/organizations/missing", headers=auth_headers).status_code == 404
    assert client.patch("/organizations/org-1", json={"status": "CUSTOMER"}, headers=auth_headers).json()["status"] == "CUSTOMER"
    assert client.delete("/organizations/org-1", headers=auth_headers).status_code == 204

    assert client.get("/departments", headers=auth_headers).json()["total"] == 1
    assert client.post("/departments", json={"name": "Sales"}, headers=auth_headers).status_code == 201
    assert client.get("/departments/dept-1", headers=auth_headers).json()["id"] == "dept-1"
    assert client.get("/departments/missing", headers=auth_headers).status_code == 404
    assert client.patch("/departments/dept-1", json={"name": "Revenue"}, headers=auth_headers).json()["name"] == "Revenue"
    assert client.delete("/departments/dept-1", headers=auth_headers).status_code == 204


def test_opportunity_quote_activity_and_product_routes(client, auth_headers):
    assert client.get("/opportunities", params={"organization_id": "org-1", "stage": "OPEN"}, headers=auth_headers).json()["total"] == 1
    assert client.post("/opportunities", json={"name": "Deal"}, headers=auth_headers).status_code == 201
    assert client.get("/opportunities/opp-1", headers=auth_headers).json()["id"] == "opp-1"
    assert client.get("/opportunities/missing", headers=auth_headers).status_code == 404
    assert client.patch("/opportunities/opp-1", json={"stage": "WON"}, headers=auth_headers).json()["stage"] == "WON"
    assert client.delete("/opportunities/opp-1", headers=auth_headers).status_code == 204
    assert client.get("/opportunities/opp-1/products", headers=auth_headers).json()[0]["opportunity_id"] == "opp-1"
    assert client.post("/opportunities/opp-1/products", json={"product_id": "prod-1"}, headers=auth_headers).status_code == 201
    assert client.delete("/opportunities/opp-1/products/line-1", headers=auth_headers).status_code == 204

    assert client.get("/quotes", params={"opportunity_id": "opp-1"}, headers=auth_headers).json()["total"] == 1
    assert client.post("/quotes", json={"name": "Quote"}, headers=auth_headers).status_code == 201
    assert client.get("/quotes/quote-1", headers=auth_headers).json()["id"] == "quote-1"
    assert client.get("/quotes/missing", headers=auth_headers).status_code == 404
    assert client.patch("/quotes/quote-1", json={"status": "SENT"}, headers=auth_headers).json()["status"] == "SENT"
    assert client.delete("/quotes/quote-1", headers=auth_headers).status_code == 204

    assert client.get("/activities", params={"status": "OPEN"}, headers=auth_headers).json()["total"] == 1
    assert client.post("/activities", json={"subject": "Call"}, headers=auth_headers).status_code == 201
    assert client.get("/activities/activity-1", headers=auth_headers).json()["id"] == "activity-1"
    assert client.get("/activities/missing", headers=auth_headers).status_code == 404
    assert client.patch("/activities/activity-1", json={"status": "DONE"}, headers=auth_headers).json()["status"] == "DONE"
    assert client.delete("/activities/activity-1", headers=auth_headers).status_code == 204

    assert client.get("/products", params={"category": "SOFTWARE"}, headers=auth_headers).json()["total"] == 1
    assert client.post("/products", json={"name": "License"}, headers=auth_headers).status_code == 201
    assert client.get("/products/product-1", headers=auth_headers).json()["id"] == "product-1"
    assert client.get("/products/missing", headers=auth_headers).status_code == 404
    assert client.patch("/products/product-1", json={"name": "Seat"}, headers=auth_headers).json()["name"] == "Seat"
    assert client.delete("/products/product-1", headers=auth_headers).status_code == 204


def test_auth_dependency_accepts_and_rejects_tokens():
    token = jwt.encode({"sub": "user-1", "email": "user@example.com"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    credentials = type("Credentials", (), {"credentials": token})()
    assert get_current_user(credentials)["user_id"] == "user-1"

    invalid = type("Credentials", (), {"credentials": "not-a-token"})()
    with pytest.raises(Exception) as exc_info:
        get_current_user(invalid)
    assert getattr(exc_info.value, "status_code", None) == 401

    no_sub = jwt.encode({"email": "user@example.com"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    no_sub_credentials = type("Credentials", (), {"credentials": no_sub})()
    with pytest.raises(Exception) as missing_sub:
        get_current_user(no_sub_credentials)
    assert getattr(missing_sub.value, "status_code", None) == 401


def test_schema_contracts_import_and_validate_payloads():
    assert crm_schemas.ContactCreate(first_name="Ada", last_name="Lovelace").first_name == "Ada"
    assert crm_schemas.OrganizationCreate(name="Croo").status == "PROSPECT"
    assert crm_schemas.OpportunityCreate(name="Deal").stage == "PROSPECTING"
    assert crm_schemas.QuoteCreate(name="Quote").status == "DRAFT"
    assert crm_schemas.ActivityCreate(subject="Call").status == "PENDING"
    assert crm_schemas.ProductCreate(name="License").currency == "CAD"
    assert crm_schemas.DepartmentCreate(name="Sales").name == "Sales"
    assert crm_schemas.OpportunityProductCreate(product_id="prod-1", unit_price=100).quantity == 1


@pytest.mark.asyncio
async def test_backend_client_methods_cover_paths(monkeypatch):
    services = {}

    def fake_factory(name):
        services.setdefault(name, FakeServiceClient(name))
        return services[name]

    monkeypatch.setattr("app.infrastructure.clients.crm_clients.create_service_client", fake_factory)

    contact_client = ContactClient()
    org_client = OrgClient()
    opportunity_client = OpportunityClient()
    activity_client = ActivityClient()
    product_client = ProductClient()

    assert (await contact_client.list(1, 2, "ada", "org-1"))["skip"] == 1
    assert await contact_client.get("missing") is None
    assert (await contact_client.get("contact-1"))["id"] == "contact-1"
    assert (await contact_client.create({"name": "Ada"}))["name"] == "Ada"
    assert (await contact_client.update("contact-1", {"status": "ACTIVE"}))["status"] == "ACTIVE"
    assert await contact_client.delete("contact-1") is True

    assert (await org_client.list(1, 2, "croo"))["limit"] == 2
    assert await org_client.get("missing") is None
    assert (await org_client.get("org-1"))["id"] == "org-1"
    assert (await org_client.create({"name": "Croo"}))["name"] == "Croo"
    assert (await org_client.update("org-1", {"status": "CUSTOMER"}))["status"] == "CUSTOMER"
    assert await org_client.delete("org-1") is True
    assert (await org_client.list_departments())["items"][0]["kind"] == "department"
    assert (await org_client.create_department({"name": "Sales"}))["name"] == "Sales"
    assert await org_client.get_department("missing") is None
    assert (await org_client.get_department("dept-1"))["id"] == "dept-1"
    assert (await org_client.update_department("dept-1", {"name": "Revenue"}))["name"] == "Revenue"
    assert await org_client.delete_department("dept-1") is True

    assert (await opportunity_client.list(1, 2, "org-1", "OPEN"))["skip"] == 1
    assert await opportunity_client.get("missing") is None
    assert (await opportunity_client.get("opp-1"))["id"] == "opp-1"
    assert (await opportunity_client.create({"name": "Deal"}))["name"] == "Deal"
    assert (await opportunity_client.update("opp-1", {"stage": "WON"}))["stage"] == "WON"
    assert await opportunity_client.delete("opp-1") is True
    assert (await opportunity_client.list_products("opp-1"))["items"][0]["kind"] == "opportunity-product"
    assert (await opportunity_client.add_product("opp-1", {"product_id": "prod-1"}))["product_id"] == "prod-1"
    assert await opportunity_client.remove_product("opp-1", "line-1") is True
    assert (await opportunity_client.list_quotes(1, 2, "opp-1"))["skip"] == 1
    assert (await opportunity_client.create_quote({"name": "Quote"}))["name"] == "Quote"
    assert await opportunity_client.get_quote("missing") is None
    assert (await opportunity_client.get_quote("quote-1"))["id"] == "quote-1"
    assert (await opportunity_client.update_quote("quote-1", {"status": "SENT"}))["status"] == "SENT"
    assert await opportunity_client.delete_quote("quote-1") is True

    assert (await activity_client.list(1, 2, "org-1", "contact-1", "opp-1", "OPEN"))["limit"] == 2
    assert await activity_client.get("missing") is None
    assert (await activity_client.get("activity-1"))["id"] == "activity-1"
    assert (await activity_client.create({"subject": "Call"}))["subject"] == "Call"
    assert (await activity_client.update("activity-1", {"status": "DONE"}))["status"] == "DONE"
    assert await activity_client.delete("activity-1") is True

    assert (await product_client.list(1, 2, "SOFTWARE"))["skip"] == 1
    assert await product_client.get("missing") is None
    assert (await product_client.get("product-1"))["id"] == "product-1"
    assert (await product_client.create({"name": "License"}))["name"] == "License"
    assert (await product_client.update("product-1", {"name": "Seat"}))["name"] == "Seat"
    assert await product_client.delete("product-1") is True


def test_python_package_contract_loads_runtime_components():
    from crm_b4f_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (
        contact_routes,
        organization_routes,
        opportunity_routes,
        quote_routes,
        activity_routes,
        product_routes,
        department_routes,
    )
    assert contract.load_runtime_client_classes() == (
        ContactClient,
        OrgClient,
        OpportunityClient,
        ActivityClient,
        ProductClient,
    )
