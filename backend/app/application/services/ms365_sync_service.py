"""MS365 sync orchestration — incremental email + calendar sync."""

from typing import Optional
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session
import structlog

from app.config import settings
from app.domain.entities.ms365_connection import MS365Connection
from app.domain.entities.contact import Contact
from app.domain.entities.organization import Organization
from app.infrastructure.persistence.ms365_repository import MS365Repository
from app.infrastructure.external.ms365_graph_service import MS365GraphService

logger = structlog.get_logger(__name__)


class MS365SyncService:
    """Orchestrates incremental sync between MS Graph and local DB.

    Uses delta queries for efficient incremental sync.
    Auto-links synced items to CRM contacts/organizations by email matching.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = MS365Repository(db)
        self.graph = MS365GraphService()

    async def _ensure_token(self, conn: MS365Connection) -> str:
        """Ensure the connection has a valid access token, refreshing if needed."""
        if not conn.access_token or not conn.token_expires_at:
            raise ValueError("Connection has no tokens")

        access_token, new_tokens = await self.graph.ensure_valid_token(
            conn.access_token, conn.refresh_token, conn.token_expires_at,
        )

        if new_tokens:
            self.repo.update_connection(conn, {
                "access_token": new_tokens["access_token"],
                "refresh_token": new_tokens.get("refresh_token", conn.refresh_token),
                "token_expires_at": datetime.now(timezone.utc) + timedelta(seconds=new_tokens.get("expires_in", 3600)),
            })
            logger.info("ms365_token_auto_refreshed", user_id=conn.user_id)

        return access_token

    # ── Email Sync ───────────────────────────────────────────────────

    async def sync_emails(self, conn: MS365Connection) -> int:
        """Sync emails for a single connection. Returns count of synced items."""
        access_token = await self._ensure_token(conn)

        messages, new_delta = await self.graph.get_emails(
            access_token, delta_token=conn.email_delta_token,
        )

        synced_count = 0
        for msg in messages:
            # Skip deleted items in delta response
            if msg.get("@removed"):
                continue

            email_data = self._map_email(msg, conn)
            email_obj = self.repo.upsert_email(email_data, tenant_id=conn.tenant_id)

            # Auto-link to CRM
            self._auto_link_email(email_obj, conn.tenant_id)
            synced_count += 1

        # Update sync state
        update_data = {"last_email_sync": datetime.now(timezone.utc)}
        if new_delta:
            update_data["email_delta_token"] = new_delta
        self.repo.update_connection(conn, update_data)

        logger.info("ms365_email_sync_complete", user_id=conn.user_id, count=synced_count)
        return synced_count

    def _map_email(self, msg: dict, conn: MS365Connection) -> dict:
        """Map MS Graph message to SyncedEmail fields."""
        from_obj = msg.get("from", {}).get("emailAddress", {})
        to_list = [
            {"address": r.get("emailAddress", {}).get("address"), "name": r.get("emailAddress", {}).get("name")}
            for r in msg.get("toRecipients", [])
        ]
        cc_list = [
            {"address": r.get("emailAddress", {}).get("address"), "name": r.get("emailAddress", {}).get("name")}
            for r in msg.get("ccRecipients", [])
        ]

        received_at = None
        if msg.get("receivedDateTime"):
            try:
                received_at = datetime.fromisoformat(msg["receivedDateTime"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        return {
            "ms365_connection_id": conn.id,
            "user_id": conn.user_id,
            "ms_message_id": msg["id"],
            "subject": msg.get("subject"),
            "body_preview": msg.get("bodyPreview"),
            "body_html": msg.get("body", {}).get("content"),
            "from_address": from_obj.get("address"),
            "from_name": from_obj.get("name"),
            "to_addresses": to_list,
            "cc_addresses": cc_list,
            "received_at": received_at,
            "is_read": msg.get("isRead", False),
            "importance": msg.get("importance", "normal"),
            "has_attachments": msg.get("hasAttachments", False),
            "folder": "inbox",
            "conversation_id": msg.get("conversationId"),
        }

    def _auto_link_email(self, email, tenant_id: str) -> None:
        """Try to match sender email to a CRM contact/organization."""
        if not email.from_address or email.linked_contact_id:
            return

        contact = self.db.query(Contact).filter(
            Contact.email == email.from_address,
            Contact.tenant_id == tenant_id,
            Contact.is_deleted == False,
        ).first()

        if contact:
            email.linked_contact_id = contact.id
            if contact.organization_id:
                email.linked_organization_id = contact.organization_id
            self.db.commit()

    # ── Calendar Sync ────────────────────────────────────────────────

    async def sync_calendar(self, conn: MS365Connection) -> int:
        """Sync calendar events for a single connection. Returns count."""
        access_token = await self._ensure_token(conn)

        events, new_delta = await self.graph.get_calendar_events(
            access_token, delta_token=conn.calendar_delta_token,
        )

        synced_count = 0
        for ev in events:
            if ev.get("@removed"):
                continue

            event_data = self._map_event(ev, conn)
            event_obj = self.repo.upsert_event(event_data, tenant_id=conn.tenant_id)

            # Auto-link to CRM
            self._auto_link_event(event_obj, conn.tenant_id)
            synced_count += 1

        update_data = {"last_calendar_sync": datetime.now(timezone.utc)}
        if new_delta:
            update_data["calendar_delta_token"] = new_delta
        self.repo.update_connection(conn, update_data)

        logger.info("ms365_calendar_sync_complete", user_id=conn.user_id, count=synced_count)
        return synced_count

    def _map_event(self, ev: dict, conn: MS365Connection) -> dict:
        """Map MS Graph event to SyncedEvent fields."""
        start_time = None
        end_time = None
        if ev.get("start", {}).get("dateTime"):
            try:
                start_time = datetime.fromisoformat(ev["start"]["dateTime"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        if ev.get("end", {}).get("dateTime"):
            try:
                end_time = datetime.fromisoformat(ev["end"]["dateTime"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        organizer = ev.get("organizer", {}).get("emailAddress", {})
        attendees_list = [
            {
                "email": a.get("emailAddress", {}).get("address"),
                "name": a.get("emailAddress", {}).get("name"),
                "status": a.get("status", {}).get("response", "none"),
            }
            for a in ev.get("attendees", [])
        ]

        online_url = None
        if ev.get("onlineMeeting"):
            online_url = ev["onlineMeeting"].get("joinUrl")

        return {
            "ms365_connection_id": conn.id,
            "user_id": conn.user_id,
            "ms_event_id": ev["id"],
            "subject": ev.get("subject"),
            "body_html": ev.get("body", {}).get("content"),
            "location": ev.get("location", {}).get("displayName"),
            "start_time": start_time,
            "end_time": end_time,
            "is_all_day": ev.get("isAllDay", False),
            "organizer_email": organizer.get("address"),
            "organizer_name": organizer.get("name"),
            "attendees": attendees_list,
            "status": "none",
            "is_cancelled": ev.get("isCancelled", False),
            "recurrence": ev.get("recurrence"),
            "online_meeting_url": online_url,
        }

    def _auto_link_event(self, event, tenant_id: str) -> None:
        """Try to match attendee emails to CRM contacts/organizations."""
        if event.linked_contact_id or not event.attendees:
            return

        for attendee in (event.attendees or []):
            email_addr = attendee.get("email")
            if not email_addr:
                continue

            contact = self.db.query(Contact).filter(
                Contact.email == email_addr,
                Contact.tenant_id == tenant_id,
                Contact.is_deleted == False,
            ).first()

            if contact:
                event.linked_contact_id = contact.id
                if contact.organization_id:
                    event.linked_organization_id = contact.organization_id
                self.db.commit()
                break  # Link to first matched contact

    # ── Bulk Sync ────────────────────────────────────────────────────

    async def sync_all_active_connections(self) -> dict:
        """Sync emails + calendar for all active connections.

        Used by the background polling task.
        Returns dict with total counts.
        """
        connections = self.repo.get_all_active_connections()
        total_emails = 0
        total_events = 0
        errors = 0

        for conn in connections:
            try:
                total_emails += await self.sync_emails(conn)
                total_events += await self.sync_calendar(conn)
            except Exception as e:
                errors += 1
                logger.error("ms365_sync_error", user_id=conn.user_id, error=str(e))

        logger.info(
            "ms365_bulk_sync_complete",
            connections=len(connections),
            emails=total_emails,
            events=total_events,
            errors=errors,
        )
        return {"connections": len(connections), "emails": total_emails, "events": total_events, "errors": errors}

    # ── Webhook Handling ─────────────────────────────────────────────

    async def handle_webhook_notification(self, notifications: list) -> None:
        """Handle incoming MS Graph change notifications.

        Triggers targeted sync for affected users.
        """
        for notification in notifications:
            subscription_id = notification.get("subscriptionId")
            resource = notification.get("resource", "")

            # Find connection by webhook subscription ID
            conn = self.db.query(MS365Connection).filter(
                (MS365Connection.email_webhook_subscription_id == subscription_id) |
                (MS365Connection.calendar_webhook_subscription_id == subscription_id),
                MS365Connection.is_active == True,
                MS365Connection.is_deleted == False,
            ).first()

            if not conn:
                logger.warning("ms365_webhook_unknown_subscription", subscription_id=subscription_id)
                continue

            try:
                if "messages" in resource:
                    await self.sync_emails(conn)
                elif "events" in resource:
                    await self.sync_calendar(conn)
            except Exception as e:
                logger.error("ms365_webhook_sync_error", user_id=conn.user_id, error=str(e))
