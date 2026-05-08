"""HTTP client for email~backend-api — all CRUD operations."""

from typing import Optional, Dict, Any, List
from shared.services import create_service_client
from shared.infrastructure import get_logger

logger = get_logger(__name__)


class IntegrationSettingsClient:
    """HTTP client for integration settings CRUD."""

    def __init__(self):
        self._client = create_service_client("email~backend-api")

    async def list(self, forward_headers=None) -> list:
        resp = await self._client.get("/api/v1/integration-settings", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json().get("items", [])

    async def upsert(self, data: dict, forward_headers=None) -> dict:
        resp = await self._client.post("/api/v1/integration-settings", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get(self, integration_key: str, forward_headers=None) -> Optional[dict]:
        items = await self.list(forward_headers=forward_headers)
        for item in items:
            if item.get("integration_key") == integration_key:
                return item
        return None

    async def update(self, integration_key: str, data: dict, forward_headers=None) -> dict:
        resp = await self._client.patch(f"/api/v1/integration-settings/{integration_key}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, integration_key: str, forward_headers=None) -> bool:
        resp = await self._client.delete(f"/api/v1/integration-settings/{integration_key}", forward_headers=forward_headers)
        return resp.status_code == 204


class ConnectionClient:
    """HTTP client for MS365 connection CRUD."""

    def __init__(self):
        self._client = create_service_client("email~backend-api")

    async def get_by_user(self, user_id: str, forward_headers=None) -> Optional[dict]:
        resp = await self._client.get(f"/api/v1/connections/by-user/{user_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        # #region agent log cf6b4c – capture 500 body
        if resp.status_code >= 400:
            body_text = resp.text
            raise Exception(f"CONN_CLIENT|{resp.status_code}|{body_text[:2000]}")
        # #endregion
        data = resp.json()
        return data if data else None

    async def get(self, conn_id: str, forward_headers=None) -> Optional[dict]:
        resp = await self._client.get(f"/api/v1/connections/{conn_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def list_active(self, forward_headers=None) -> list:
        resp = await self._client.get("/api/v1/connections/active/all", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create(self, data: dict, forward_headers=None) -> dict:
        resp = await self._client.post("/api/v1/connections", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update(self, conn_id: str, data: dict, forward_headers=None) -> dict:
        resp = await self._client.patch(f"/api/v1/connections/{conn_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, conn_id: str, forward_headers=None) -> bool:
        resp = await self._client.delete(f"/api/v1/connections/{conn_id}", forward_headers=forward_headers)
        return resp.status_code == 204


class EmailCrudClient:
    """HTTP client for synced email CRUD."""

    def __init__(self):
        self._client = create_service_client("email~backend-api")

    async def list(self, user_id: str, skip=0, limit=50, folder=None, search=None, smart_label=None, linked_contact_id=None, forward_headers=None) -> dict:
        params: Dict[str, str] = {"user_id": user_id, "skip": str(skip), "limit": str(limit)}
        if folder:
            params["folder"] = folder
        if search:
            params["search"] = search
        if smart_label:
            params["smart_label"] = smart_label
        if linked_contact_id:
            params["linked_contact_id"] = linked_contact_id
        resp = await self._client.get("/api/v1/emails", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get(self, email_id: str, user_id: str, forward_headers=None) -> Optional[dict]:
        params = {"user_id": user_id}
        resp = await self._client.get(f"/api/v1/emails/{email_id}", params=params, forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def upsert(self, data: dict, forward_headers=None) -> dict:
        resp = await self._client.post("/api/v1/emails", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update(self, email_id: str, data: dict, user_id: str, forward_headers=None) -> dict:
        params = {"user_id": user_id}
        resp = await self._client.patch(f"/api/v1/emails/{email_id}", json=data, params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, email_id: str, user_id: str, forward_headers=None) -> bool:
        params = {"user_id": user_id}
        resp = await self._client.delete(f"/api/v1/emails/{email_id}", params=params, forward_headers=forward_headers)
        return resp.status_code == 204


class EventCrudClient:
    """HTTP client for synced event CRUD."""

    def __init__(self):
        self._client = create_service_client("email~backend-api")

    async def list(self, user_id: str, skip=0, limit=50, from_date=None, to_date=None, forward_headers=None) -> dict:
        params: Dict[str, str] = {"user_id": user_id, "skip": str(skip), "limit": str(limit)}
        if from_date:
            params["from_date"] = from_date.isoformat() if hasattr(from_date, 'isoformat') else str(from_date)
        if to_date:
            params["to_date"] = to_date.isoformat() if hasattr(to_date, 'isoformat') else str(to_date)
        resp = await self._client.get("/api/v1/events", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get(self, event_id: str, user_id: str, forward_headers=None) -> Optional[dict]:
        params = {"user_id": user_id}
        resp = await self._client.get(f"/api/v1/events/{event_id}", params=params, forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def upsert(self, data: dict, forward_headers=None) -> dict:
        resp = await self._client.post("/api/v1/events", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update(self, event_id: str, data: dict, user_id: str, forward_headers=None) -> dict:
        params = {"user_id": user_id}
        resp = await self._client.patch(f"/api/v1/events/{event_id}", json=data, params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, event_id: str, user_id: str, forward_headers=None) -> bool:
        params = {"user_id": user_id}
        resp = await self._client.delete(f"/api/v1/events/{event_id}", params=params, forward_headers=forward_headers)
        return resp.status_code == 204


class SmartLabelClient:
    """HTTP client for smart label CRUD."""

    def __init__(self):
        self._client = create_service_client("email~backend-api")

    async def list(self, skip=0, limit=50, forward_headers=None) -> dict:
        params = {"skip": str(skip), "limit": str(limit)}
        resp = await self._client.get("/api/v1/smart-labels", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get(self, label_id: str, forward_headers=None) -> Optional[dict]:
        resp = await self._client.get(f"/api/v1/smart-labels/{label_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def create(self, data: dict, forward_headers=None) -> dict:
        resp = await self._client.post("/api/v1/smart-labels", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def update(self, label_id: str, data: dict, forward_headers=None) -> dict:
        resp = await self._client.patch(f"/api/v1/smart-labels/{label_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, label_id: str, forward_headers=None) -> bool:
        resp = await self._client.delete(f"/api/v1/smart-labels/{label_id}", forward_headers=forward_headers)
        return resp.status_code == 204


class MembraneCrudClient:
    """HTTP client for Membrane-backed CRUD in email~backend-api."""

    def __init__(self):
        self._client = create_service_client("email~backend-api")

    async def upsert_connection(self, data: dict, forward_headers=None) -> dict:
        resp = await self._client.post("/api/v1/membrane/connections", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_connection(self, connection_id: str, forward_headers=None) -> Optional[dict]:
        resp = await self._client.get(f"/api/v1/membrane/connections/{connection_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def upsert_email(self, data: dict, forward_headers=None) -> dict:
        resp = await self._client.post("/api/v1/membrane/emails", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def upsert_event(self, data: dict, forward_headers=None) -> dict:
        resp = await self._client.post("/api/v1/membrane/events", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_connection_by_user(self, user_id: str, integration_key: Optional[str] = None, forward_headers=None) -> Optional[dict]:
        params = {}
        if integration_key:
            params["integration_key"] = integration_key
        resp = await self._client.get(f"/api/v1/membrane/connections/by-user/{user_id}", params=params, forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def list_emails(self, user_id: str, skip: int = 0, limit: int = 50, folder: Optional[str] = None, search: Optional[str] = None, forward_headers=None) -> dict:
        params: Dict[str, str] = {"user_id": user_id, "skip": str(skip), "limit": str(limit)}
        if folder:
            params["folder"] = folder
        if search:
            params["search"] = search
        resp = await self._client.get("/api/v1/membrane/emails", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def list_events(self, user_id: str, skip: int = 0, limit: int = 50, from_date: Optional[str] = None, to_date: Optional[str] = None, forward_headers=None) -> dict:
        params: Dict[str, str] = {"user_id": user_id, "skip": str(skip), "limit": str(limit)}
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        resp = await self._client.get("/api/v1/membrane/events", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()


connection_client = ConnectionClient()
email_crud_client = EmailCrudClient()
event_crud_client = EventCrudClient()
smart_label_client = SmartLabelClient()
integration_settings_client = IntegrationSettingsClient()
membrane_crud_client = MembraneCrudClient()
