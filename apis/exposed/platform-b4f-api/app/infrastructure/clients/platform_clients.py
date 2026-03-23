"""HTTP clients for platform backend services."""
from typing import Optional, Dict, Any, List
from shared.services import create_service_client
from shared.infrastructure import get_logger

logger = get_logger(__name__)


class WorkflowClient:
    def __init__(self):
        self._client = create_service_client("workflow~backend-api")

    async def list(self, skip=0, limit=50, level=None, module=None, is_template=None, forward_headers=None):
        params = {"skip": str(skip), "limit": str(limit)}
        if level:
            params["level"] = level
        if module:
            params["module"] = module
        if is_template is not None:
            params["is_template"] = str(is_template).lower()
        resp = await self._client.get("/api/v1/workflows", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get(self, wf_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/workflows/{wf_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def create(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/workflows", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update(self, wf_id, data, forward_headers=None):
        resp = await self._client.patch(f"/api/v1/workflows/{wf_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, wf_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/workflows/{wf_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    # Steps
    async def list_steps(self, wf_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/workflows/{wf_id}/steps", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def add_step(self, wf_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/workflows/{wf_id}/steps", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update_step(self, wf_id, step_id, data, forward_headers=None):
        resp = await self._client.patch(f"/api/v1/workflows/{wf_id}/steps/{step_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_step(self, wf_id, step_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/workflows/{wf_id}/steps/{step_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    # Executions
    async def create_execution(self, wf_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/workflows/{wf_id}/executions", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def list_executions(self, wf_id, limit=20, forward_headers=None):
        params = {"limit": str(limit)}
        resp = await self._client.get(f"/api/v1/workflows/{wf_id}/executions", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_execution(self, wf_id, exe_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/workflows/{wf_id}/executions/{exe_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def update_execution(self, wf_id, exe_id, data, forward_headers=None):
        resp = await self._client.patch(f"/api/v1/workflows/{wf_id}/executions/{exe_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    # Monitoring
    async def get_monitoring_stats(self, forward_headers=None):
        resp = await self._client.get("/api/v1/workflows/monitoring/stats", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_recent_executions(self, limit=20, status_filter=None, forward_headers=None):
        params = {"limit": str(limit)}
        if status_filter:
            params["status"] = status_filter
        resp = await self._client.get("/api/v1/workflows/monitoring/recent", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()


class UsageClient:
    def __init__(self):
        self._client = create_service_client("usage~backend-api")

    async def record(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/usage", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def list(self, skip=0, limit=50, service_type=None, billing_category=None, user_id=None, date_from=None, date_to=None, forward_headers=None):
        params = {"skip": str(skip), "limit": str(limit)}
        if service_type:
            params["service_type"] = service_type
        if billing_category:
            params["billing_category"] = billing_category
        if user_id:
            params["user_id"] = user_id
        if date_from:
            params["date_from"] = str(date_from)
        if date_to:
            params["date_to"] = str(date_to)
        resp = await self._client.get("/api/v1/usage", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_summary(self, date_from=None, date_to=None, forward_headers=None):
        params = {}
        if date_from:
            params["date_from"] = str(date_from)
        if date_to:
            params["date_to"] = str(date_to)
        resp = await self._client.get("/api/v1/usage/summary", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    # Admin
    async def admin_list(self, tenant_id=None, skip=0, limit=50, service_type=None, billing_category=None, user_id=None, date_from=None, date_to=None, forward_headers=None):
        params = {"skip": str(skip), "limit": str(limit)}
        if tenant_id:
            params["tenant_id"] = tenant_id
        if service_type:
            params["service_type"] = service_type
        if billing_category:
            params["billing_category"] = billing_category
        if user_id:
            params["user_id"] = user_id
        if date_from:
            params["date_from"] = str(date_from)
        if date_to:
            params["date_to"] = str(date_to)
        resp = await self._client.get("/api/v1/admin/usage", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def admin_summary(self, tenant_id, date_from=None, date_to=None, forward_headers=None):
        params = {"tenant_id": tenant_id}
        if date_from:
            params["date_from"] = str(date_from)
        if date_to:
            params["date_to"] = str(date_to)
        resp = await self._client.get("/api/v1/admin/usage/summary", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def admin_by_intent(self, tenant_id=None, skip=0, limit=50, forward_headers=None):
        params = {"skip": str(skip), "limit": str(limit)}
        if tenant_id:
            params["tenant_id"] = tenant_id
        resp = await self._client.get("/api/v1/admin/usage/by-intent", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def admin_intent_detail(self, correlation_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/admin/usage/by-intent/{correlation_id}", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def list_rate_cards(self, active_only=True, forward_headers=None):
        params = {"active_only": str(active_only).lower()}
        resp = await self._client.get("/api/v1/rate-cards", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_rate_card(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/rate-cards", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()


workflow_client = WorkflowClient()
usage_client = UsageClient()
