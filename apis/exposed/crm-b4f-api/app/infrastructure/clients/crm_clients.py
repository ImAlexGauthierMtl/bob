"""HTTP clients for CRM backend services."""
from typing import Optional, Dict, Any, List
from shared.services import create_service_client
from shared.infrastructure import get_logger

logger = get_logger(__name__)


class ContactClient:
    def __init__(self):
        self._client = create_service_client("contact~backend-api")

    async def list(self, skip=0, limit=50, search=None, organization_id=None, forward_headers=None):
        params = {"skip": str(skip), "limit": str(limit)}
        if search:
            params["search"] = search
        if organization_id:
            params["organization_id"] = organization_id
        resp = await self._client.get("/api/v1/contacts", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get(self, contact_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/contacts/{contact_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def create(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/contacts", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update(self, contact_id, data, forward_headers=None):
        resp = await self._client.patch(f"/api/v1/contacts/{contact_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, contact_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/contacts/{contact_id}", forward_headers=forward_headers)
        return resp.status_code == 204


class OrgClient:
    def __init__(self):
        self._client = create_service_client("org~backend-api")

    async def list(self, skip=0, limit=50, search=None, forward_headers=None):
        params = {"skip": str(skip), "limit": str(limit)}
        if search:
            params["search"] = search
        resp = await self._client.get("/api/v1/organizations", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get(self, org_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/organizations/{org_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def create(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/organizations", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update(self, org_id, data, forward_headers=None):
        resp = await self._client.patch(f"/api/v1/organizations/{org_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, org_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/organizations/{org_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def list_departments(self, forward_headers=None):
        resp = await self._client.get("/api/v1/departments", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_department(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/departments", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_department(self, dept_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/departments/{dept_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def update_department(self, dept_id, data, forward_headers=None):
        resp = await self._client.patch(f"/api/v1/departments/{dept_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_department(self, dept_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/departments/{dept_id}", forward_headers=forward_headers)
        return resp.status_code == 204


class OpportunityClient:
    def __init__(self):
        self._client = create_service_client("opportunity~backend-api")

    async def list(self, skip=0, limit=50, organization_id=None, stage=None, forward_headers=None):
        params = {"skip": str(skip), "limit": str(limit)}
        if organization_id:
            params["organization_id"] = organization_id
        if stage:
            params["stage"] = stage
        resp = await self._client.get("/api/v1/opportunities", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get(self, opp_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/opportunities/{opp_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def create(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/opportunities", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update(self, opp_id, data, forward_headers=None):
        resp = await self._client.patch(f"/api/v1/opportunities/{opp_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, opp_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/opportunities/{opp_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def list_products(self, opp_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/opportunities/{opp_id}/products", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def add_product(self, opp_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/opportunities/{opp_id}/products", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def remove_product(self, opp_id, line_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/opportunities/{opp_id}/products/{line_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def list_quotes(self, skip=0, limit=50, opportunity_id=None, forward_headers=None):
        params = {"skip": str(skip), "limit": str(limit)}
        if opportunity_id:
            params["opportunity_id"] = opportunity_id
        resp = await self._client.get("/api/v1/quotes", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_quote(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/quotes", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_quote(self, quote_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/quotes/{quote_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def update_quote(self, quote_id, data, forward_headers=None):
        resp = await self._client.patch(f"/api/v1/quotes/{quote_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_quote(self, quote_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/quotes/{quote_id}", forward_headers=forward_headers)
        return resp.status_code == 204


class ActivityClient:
    def __init__(self):
        self._client = create_service_client("activity~backend-api")

    async def list(self, skip=0, limit=50, organization_id=None, contact_id=None, opportunity_id=None, status=None, forward_headers=None):
        params = {"skip": str(skip), "limit": str(limit)}
        if organization_id:
            params["organization_id"] = organization_id
        if contact_id:
            params["contact_id"] = contact_id
        if opportunity_id:
            params["opportunity_id"] = opportunity_id
        if status:
            params["status"] = status
        resp = await self._client.get("/api/v1/activities", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get(self, activity_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/activities/{activity_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def create(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/activities", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update(self, activity_id, data, forward_headers=None):
        resp = await self._client.patch(f"/api/v1/activities/{activity_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, activity_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/activities/{activity_id}", forward_headers=forward_headers)
        return resp.status_code == 204


class ProductClient:
    def __init__(self):
        self._client = create_service_client("product~backend-api")

    async def list(self, skip=0, limit=50, category=None, forward_headers=None):
        params = {"skip": str(skip), "limit": str(limit)}
        if category:
            params["category"] = category
        resp = await self._client.get("/api/v1/products", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get(self, product_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/products/{product_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def create(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/products", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update(self, product_id, data, forward_headers=None):
        resp = await self._client.patch(f"/api/v1/products/{product_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, product_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/products/{product_id}", forward_headers=forward_headers)
        return resp.status_code == 204


contact_client = ContactClient()
org_client = OrgClient()
opportunity_client = OpportunityClient()
activity_client = ActivityClient()
product_client = ProductClient()
