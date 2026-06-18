"""Integration overview composition service."""

import asyncio
from typing import Any


class IntegrationOverviewService:
    """Compose communication integration state for the frontend."""

    def __init__(self, integration_settings_client, connection_client, membrane_crud_client, smart_label_client):
        self.integration_settings_client = integration_settings_client
        self.connection_client = connection_client
        self.membrane_crud_client = membrane_crud_client
        self.smart_label_client = smart_label_client

    async def build_overview(self, current_user: dict, forward_headers: Any = None) -> dict:
        user_id = current_user["user_id"]
        settings = await self.integration_settings_client.list(forward_headers=forward_headers)
        smart_labels, ms365_connection, membrane_connections = await asyncio.gather(
            self.smart_label_client.list(skip=0, limit=10, forward_headers=forward_headers),
            self.connection_client.get_by_user(user_id, forward_headers=forward_headers),
            self._load_membrane_connections(user_id, settings, forward_headers),
        )

        integrations = [
            self._integration_state(item, ms365_connection, membrane_connections.get(item.get("integration_key")))
            for item in settings
        ]
        return {
            "user_id": user_id,
            "tenant_id": current_user.get("tenant_id"),
            "integrations": integrations,
            "smart_labels": self._items(smart_labels),
            "totals": {
                "configured": len(integrations),
                "enabled": sum(1 for item in integrations if item["is_enabled"]),
                "connected": sum(1 for item in integrations if item["is_connected"]),
                "smart_labels": self._total(smart_labels),
            },
        }

    async def _load_membrane_connections(self, user_id: str, settings: list[dict], forward_headers: Any) -> dict:
        async def load(setting: dict) -> tuple[str, dict | None]:
            integration_key = setting.get("integration_key")
            connection = await self.membrane_crud_client.get_connection_by_user(
                user_id,
                integration_key=integration_key,
                forward_headers=forward_headers,
            )
            return integration_key, connection

        loaded = await asyncio.gather(*(load(setting) for setting in settings if setting.get("integration_key")))
        return {key: value for key, value in loaded if key}

    @staticmethod
    def _integration_state(setting: dict, ms365_connection: dict | None, membrane_connection: dict | None) -> dict:
        integration_key = setting.get("integration_key")
        legacy_ms365_connected = integration_key == "microsoft-outlook" and bool(ms365_connection)
        is_connected = bool(membrane_connection) or legacy_ms365_connected
        return {
            "integration_key": integration_key,
            "display_name": setting.get("display_name") or integration_key,
            "scope_mode": setting.get("scope_mode"),
            "is_enabled": bool(setting.get("is_enabled")),
            "is_connected": is_connected,
            "connection_id": (membrane_connection or ms365_connection or {}).get("id"),
            "connection_provider": "membrane" if membrane_connection else ("ms365" if legacy_ms365_connected else None),
        }

    @staticmethod
    def _items(payload: Any) -> list:
        if isinstance(payload, dict):
            items = payload.get("items", [])
            return items if isinstance(items, list) else []
        return payload if isinstance(payload, list) else []

    def _total(self, payload: Any) -> int:
        if isinstance(payload, dict) and isinstance(payload.get("total"), int):
            return payload["total"]
        return len(self._items(payload))
