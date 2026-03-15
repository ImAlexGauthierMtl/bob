"""HTTP client for user~backend-api."""
from typing import Optional, Dict, Any, List
from shared.services import create_service_client, HTTPClient
from shared.infrastructure import get_logger

logger = get_logger(__name__)

class UserClient:
    def __init__(self):
        self._client: HTTPClient = create_service_client("user~backend-api")

    async def get_by_id(self, user_id: str, forward_headers: Any = None) -> Optional[Dict]:
        resp = await self._client.get(f"/api/v1/users/{user_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def get_by_email(self, email: str, forward_headers: Any = None) -> Optional[Dict]:
        resp = await self._client.get(f"/api/v1/users/by-email/{email}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def create(self, data: Dict[str, Any], forward_headers: Any = None) -> Dict:
        resp = await self._client.post("/api/v1/users", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update(self, user_id: str, data: Dict[str, Any], forward_headers: Any = None) -> Dict:
        resp = await self._client.patch(f"/api/v1/users/{user_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, user_id: str, forward_headers: Any = None) -> bool:
        resp = await self._client.delete(f"/api/v1/users/{user_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def list_users(self, skip: int = 0, limit: int = 50, forward_headers: Any = None) -> Dict:
        resp = await self._client.get("/api/v1/users", params={"skip": str(skip), "limit": str(limit)}, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_user_roles(self, user_id: str, forward_headers: Any = None) -> List[Dict]:
        resp = await self._client.get(f"/api/v1/roles/users/{user_id}/roles", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json().get("roles", [])

    async def get_user_permissions(self, user_id: str, forward_headers: Any = None) -> List[str]:
        resp = await self._client.get(f"/api/v1/roles/users/{user_id}/permissions", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json().get("permissions", [])


class TenantClient:
    def __init__(self):
        self._client: HTTPClient = create_service_client("user~backend-api")

    async def get_by_id(self, tenant_id: str, forward_headers: Any = None) -> Optional[Dict]:
        resp = await self._client.get(f"/api/v1/tenants/{tenant_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def get_by_slug(self, slug: str, forward_headers: Any = None) -> Optional[Dict]:
        resp = await self._client.get(f"/api/v1/tenants/by-slug/{slug}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def create(self, data: Dict[str, Any], forward_headers: Any = None) -> Dict:
        resp = await self._client.post("/api/v1/tenants", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update(self, tenant_id: str, data: Dict[str, Any], forward_headers: Any = None) -> Dict:
        resp = await self._client.patch(f"/api/v1/tenants/{tenant_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, tenant_id: str, forward_headers: Any = None) -> bool:
        resp = await self._client.delete(f"/api/v1/tenants/{tenant_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def list_tenants(self, search: str = None, status: str = None, skip: int = 0, limit: int = 50, forward_headers: Any = None) -> Dict:
        params = {"skip": str(skip), "limit": str(limit)}
        if search:
            params["search"] = search
        if status:
            params["status"] = status
        resp = await self._client.get("/api/v1/tenants", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()


class RoleClient:
    def __init__(self):
        self._client: HTTPClient = create_service_client("user~backend-api")

    async def list_roles(self, forward_headers: Any = None) -> Dict:
        resp = await self._client.get("/api/v1/roles", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_role(self, data: Dict, forward_headers: Any = None) -> Dict:
        resp = await self._client.post("/api/v1/roles", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_role(self, role_id: str, forward_headers: Any = None) -> Optional[Dict]:
        resp = await self._client.get(f"/api/v1/roles/{role_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def update_role(self, role_id: str, data: Dict, forward_headers: Any = None) -> Dict:
        resp = await self._client.patch(f"/api/v1/roles/{role_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_role(self, role_id: str, forward_headers: Any = None) -> bool:
        resp = await self._client.delete(f"/api/v1/roles/{role_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def set_permissions(self, role_id: str, permission_ids: List[str], forward_headers: Any = None) -> Dict:
        resp = await self._client.put(f"/api/v1/roles/{role_id}/permissions", json={"permission_ids": permission_ids}, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def list_permissions(self, forward_headers: Any = None) -> List[Dict]:
        resp = await self._client.get("/api/v1/roles/permissions", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def assign_role(self, user_id: str, role_id: str, forward_headers: Any = None) -> None:
        resp = await self._client.post(f"/api/v1/roles/users/{user_id}/roles", json={"role_id": role_id}, forward_headers=forward_headers)
        resp.raise_for_status()

    async def remove_role(self, user_id: str, role_id: str, forward_headers: Any = None) -> None:
        await self._client.delete(f"/api/v1/roles/users/{user_id}/roles/{role_id}", forward_headers=forward_headers)


user_client = UserClient()
tenant_client = TenantClient()
role_client = RoleClient()
