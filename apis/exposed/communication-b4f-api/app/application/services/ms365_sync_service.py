"""MS365 Sync Service — orchestrates sync via HTTP client to email~backend-api."""

from datetime import datetime, timezone
from typing import Union, Dict, Any, Optional

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


def _graph_msg_to_upsert(msg: Dict[str, Any], connection_id: str, user_id: str) -> Dict[str, Any]:
    """Transform a raw MS Graph message into EmailUpsertRequest-compatible dict."""
    from_obj = msg.get("from", {}).get("emailAddress", {})
    to_list = [
        {"address": r.get("emailAddress", {}).get("address", ""), "name": r.get("emailAddress", {}).get("name", "")}
        for r in msg.get("toRecipients", [])
    ]
    cc_list = [
        {"address": r.get("emailAddress", {}).get("address", ""), "name": r.get("emailAddress", {}).get("name", "")}
        for r in msg.get("ccRecipients", [])
    ]

    received = msg.get("receivedDateTime")

    return {
        "ms365_connection_id": connection_id,
        "user_id": user_id,
        "ms_message_id": msg.get("id", ""),
        "subject": msg.get("subject"),
        "body_preview": msg.get("bodyPreview"),
        "body_html": (msg.get("body") or {}).get("content"),
        "from_address": from_obj.get("address"),
        "from_name": from_obj.get("name"),
        "to_addresses": to_list or None,
        "cc_addresses": cc_list or None,
        "received_at": received,
        "is_read": msg.get("isRead", False),
        "importance": msg.get("importance", "normal"),
        "has_attachments": msg.get("hasAttachments", False),
        "folder": (msg.get("parentFolderId") or "inbox")[:255],
        "conversation_id": msg.get("conversationId"),
    }


def _graph_event_to_upsert(ev: Dict[str, Any], connection_id: str, user_id: str) -> Dict[str, Any]:
    """Transform a raw MS Graph event into EventUpsertRequest-compatible dict."""
    organizer = ev.get("organizer", {}).get("emailAddress", {})
    start = ev.get("start", {})
    end = ev.get("end", {})
    attendees = [
        {
            "email": a.get("emailAddress", {}).get("address", ""),
            "name": a.get("emailAddress", {}).get("name", ""),
            "status": (a.get("status") or {}).get("response", "none"),
        }
        for a in ev.get("attendees", [])
    ]
    location = ev.get("location", {})
    location_str = location.get("displayName") if isinstance(location, dict) else str(location) if location else None

    return {
        "ms365_connection_id": connection_id,
        "user_id": user_id,
        "ms_event_id": ev.get("id", ""),
        "subject": ev.get("subject"),
        "body_html": (ev.get("body") or {}).get("content"),
        "location": location_str,
        "start_time": start.get("dateTime"),
        "end_time": end.get("dateTime"),
        "is_all_day": ev.get("isAllDay", False),
        "organizer_email": organizer.get("address"),
        "organizer_name": organizer.get("name"),
        "attendees": attendees or None,
        "status": "none",
        "is_cancelled": ev.get("isCancelled", False),
        "recurrence": ev.get("recurrence"),
        "online_meeting_url": ev.get("onlineMeetingUrl"),
    }


class MS365SyncService:
    """Sync orchestration — business logic stays here, CRUD via HTTP."""

    def __init__(self, forward_headers=None):
        self._headers = forward_headers

    async def sync_emails(self, connection: dict) -> int:
        """Sync emails from MS365 via Graph API, persist via backend."""
        from app.infrastructure.external.ms365_graph_service import MS365GraphService
        graph = MS365GraphService()

        connection_id = connection["id"]
        user_id = connection["user_id"]
        access_token = connection.get("access_token")
        refresh_token = connection.get("refresh_token")
        expires_at = _parse_expires_at(connection.get("token_expires_at"))

        try:
            access_token, new_data = await graph.ensure_valid_token(access_token, refresh_token, expires_at)
            if new_data:
                await connection_client.update(connection_id, new_data, forward_headers=self._headers)
        except Exception as e:
            await connection_client.update(
                connection_id,
                {"is_active": False, "connection_status": "token_expired"},
                forward_headers=self._headers,
            )
            raise e

        total_synced = 0
        async for messages, _page, _total in graph.get_emails_batched(access_token, connection.get("email_delta_token")):
            for msg in messages:
                upsert_data = _graph_msg_to_upsert(msg, connection_id, user_id)
                await email_crud_client.upsert(upsert_data, forward_headers=self._headers)
                total_synced += 1
            if hasattr(graph, "_last_delta_token") and graph._last_delta_token:
                await connection_client.update(
                    connection_id,
                    {"email_delta_token": graph._last_delta_token, "last_email_sync": datetime.now(timezone.utc).isoformat()},
                    forward_headers=self._headers,
                )

        return total_synced

    async def sync_calendar(self, connection: dict) -> int:
        """Sync calendar from MS365 via Graph API, persist via backend."""
        from app.infrastructure.external.ms365_graph_service import MS365GraphService
        graph = MS365GraphService()

        connection_id = connection["id"]
        user_id = connection["user_id"]
        access_token = connection.get("access_token")
        refresh_token = connection.get("refresh_token")
        expires_at = _parse_expires_at(connection.get("token_expires_at"))

        try:
            access_token, new_data = await graph.ensure_valid_token(access_token, refresh_token, expires_at)
            if new_data:
                await connection_client.update(connection_id, new_data, forward_headers=self._headers)
        except Exception as e:
            await connection_client.update(
                connection_id,
                {"is_active": False, "connection_status": "token_expired"},
                forward_headers=self._headers,
            )
            raise e

        # get_calendar_events returns a Tuple[List[Dict], Optional[str]]
        all_events, new_delta = await graph.get_calendar_events(access_token, connection.get("calendar_delta_token"))

        total_synced = 0
        for ev in all_events:
            upsert_data = _graph_event_to_upsert(ev, connection_id, user_id)
            await event_crud_client.upsert(upsert_data, forward_headers=self._headers)
            total_synced += 1

        update_data = {"last_calendar_sync": datetime.now(timezone.utc).isoformat()}
        if new_delta:
            update_data["calendar_delta_token"] = new_delta
        await connection_client.update(connection_id, update_data, forward_headers=self._headers)

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

