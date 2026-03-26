"""MS365 Sync Service — orchestrates sync via HTTP client to email~backend-api."""

from datetime import datetime, timezone
from typing import Union

import structlog

from app.infrastructure.clients.email_client import connection_client, email_crud_client, event_crud_client

logger = structlog.get_logger(__name__)


def _parse_expires_at(value: Union[str, datetime, None]) -> datetime:
    """Parse token_expires_at from string or datetime into a tz-aware datetime."""
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


class MS365SyncService:
    """Sync orchestration — business logic stays here, CRUD via HTTP."""

    def __init__(self, forward_headers=None):
        self._headers = forward_headers

    async def sync_emails(self, connection: dict) -> int:
        """Sync emails from MS365 via Graph API, persist via backend."""
        from app.infrastructure.external.ms365_graph_service import MS365GraphService
        graph = MS365GraphService()

        access_token = connection.get("access_token")
        refresh_token = connection.get("refresh_token")
        expires_at = _parse_expires_at(connection.get("token_expires_at"))

        try:
            access_token, new_data = await graph.ensure_valid_token(access_token, refresh_token, expires_at)
            if new_data:
                await connection_client.update(connection["id"], new_data, forward_headers=self._headers)
        except Exception as e:
            await connection_client.update(
                connection["id"],
                {"is_active": False, "connection_status": "token_expired"},
                forward_headers=self._headers,
            )
            raise e

        total_synced = 0
        async for messages, _page, _total in graph.get_emails_batched(access_token, connection.get("email_delta_token")):
            for msg in messages:
                await email_crud_client.upsert(msg, forward_headers=self._headers)
                total_synced += 1
            if hasattr(graph, "_last_delta_token") and graph._last_delta_token:
                await connection_client.update(
                    connection["id"],
                    {"email_delta_token": graph._last_delta_token, "last_email_sync": datetime.now(timezone.utc).isoformat()},
                    forward_headers=self._headers,
                )

        return total_synced

    async def sync_calendar(self, connection: dict) -> int:
        """Sync calendar from MS365 via Graph API, persist via backend."""
        from app.infrastructure.external.ms365_graph_service import MS365GraphService
        graph = MS365GraphService()

        access_token = connection.get("access_token")
        refresh_token = connection.get("refresh_token")
        expires_at = _parse_expires_at(connection.get("token_expires_at"))

        try:
            access_token, new_data = await graph.ensure_valid_token(access_token, refresh_token, expires_at)
            if new_data:
                await connection_client.update(connection["id"], new_data, forward_headers=self._headers)
        except Exception as e:
            await connection_client.update(
                connection["id"],
                {"is_active": False, "connection_status": "token_expired"},
                forward_headers=self._headers,
            )
            raise e

        # get_calendar_events returns a Tuple[List[Dict], Optional[str]]
        all_events, new_delta = await graph.get_calendar_events(access_token, connection.get("calendar_delta_token"))

        total_synced = 0
        for ev in all_events:
            await event_crud_client.upsert(ev, forward_headers=self._headers)
            total_synced += 1

        update_data = {"last_calendar_sync": datetime.now(timezone.utc).isoformat()}
        if new_delta:
            update_data["calendar_delta_token"] = new_delta
        await connection_client.update(connection["id"], update_data, forward_headers=self._headers)

        return total_synced

    async def handle_webhook_notification(self, notifications: list) -> None:
        """Handle webhook notification from MS Graph.
        For each notification, trigger a sync for the associated connection.
        """
        active_conns = await connection_client.list_active(forward_headers=self._headers)
        for conn in active_conns:
            try:
                await self.sync_emails(conn)
                await self.sync_calendar(conn)
            except Exception as e:
                logger.error("ms365_webhook_sync_error", connection_id=conn.get("id"), error=str(e))
