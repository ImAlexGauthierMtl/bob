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
        """Sync emails for a single connection using page-by-page streaming.

        Processes and commits each page of ~50 emails independently so memory
        stays constant regardless of mailbox size.
        """
        access_token = await self._ensure_token(conn)

        synced_count = 0
        skipped_count = 0
        async for page_msgs, page_num, total_so_far in self.graph.get_emails_batched(
            access_token, delta_token=conn.email_delta_token,
        ):
            page_count = 0
            for msg in page_msgs:
                if msg.get("@removed"):
                    continue
                try:
                    email_data = self._map_email(msg, conn)
                    email_obj = self.repo.upsert_email(email_data, tenant_id=conn.tenant_id)
                    self._auto_link_email(email_obj, conn.tenant_id)
                    page_count += 1
                except Exception as e:
                    self.db.rollback()
                    skipped_count += 1
                    logger.warning(
                        "ms365_email_skipped",
                        ms_message_id=msg.get("id", "?")[:60],
                        error=str(e)[:200],
                    )

            self.db.commit()
            synced_count += page_count
            logger.info(
                "ms365_email_batch_committed",
                user_id=conn.user_id, page=page_num,
                page_count=page_count, synced_so_far=synced_count,
                skipped=skipped_count,
            )

        new_delta = await self.graph.acquire_delta_token(access_token)

        update_data = {"last_email_sync": datetime.now(timezone.utc)}
        if new_delta:
            update_data["email_delta_token"] = new_delta
        self.repo.update_connection(conn, update_data)

        logger.info("ms365_email_sync_complete", user_id=conn.user_id, count=synced_count)
        return synced_count

    @staticmethod
    def _trunc(value: Optional[str], max_len: int) -> Optional[str]:
        if value and len(value) > max_len:
            return value[:max_len]
        return value

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
            "ms_message_id": self._trunc(msg["id"], 255),
            "subject": self._trunc(msg.get("subject"), 500),
            "body_preview": msg.get("bodyPreview"),
            "body_html": msg.get("body", {}).get("content"),
            "from_address": self._trunc(from_obj.get("address"), 255),
            "from_name": self._trunc(from_obj.get("name"), 255),
            "to_addresses": to_list,
            "cc_addresses": cc_list,
            "received_at": received_at,
            "is_read": msg.get("isRead", False),
            "importance": msg.get("importance", "normal"),
            "has_attachments": msg.get("hasAttachments", False),
            "folder": "inbox",
            "conversation_id": self._trunc(msg.get("conversationId"), 255),
        }

    def _auto_link_email(self, email, tenant_id: str) -> None:
        """Link email to ALL involved contacts (from + to + cc).
        
        For each address: find or create a Contact (+ Organization from domain).
        Inserts rows into email_contacts junction table with role.
        Keeps backward-compat linked_contact_id pointed at the sender.
        """
        import tldextract
        from app.domain.entities.organization import Organization
        from app.domain.entities.email_contact import email_contacts

        PUBLIC_DOMAINS = {
            "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com",
            "icloud.com", "me.com", "msn.com", "googlemail.com", "aol.com",
            "protonmail.com", "zoho.com", "ymail.com",
        }

        # Collect all addresses with roles
        addresses: list[dict] = []
        if email.from_address:
            addresses.append({"address": email.from_address.lower().strip(), "name": email.from_name or "", "role": "from"})

        for recipient_list, role in [(email.to_addresses, "to"), (email.cc_addresses, "cc")]:
            if not recipient_list:
                continue
            for r in recipient_list:
                addr = (r.get("address") or "").lower().strip()
                if addr:
                    addresses.append({"address": addr, "name": r.get("name", ""), "role": role})

        # De-duplicate by address (keep first role encountered)
        seen = set()
        unique_addresses = []
        for a in addresses:
            if a["address"] not in seen:
                seen.add(a["address"])
                unique_addresses.append(a)

        sender_contact = None

        for entry in unique_addresses:
            addr = entry["address"]
            name = entry["name"]
            role = entry["role"]

            # 1. Find existing contact
            contact = self.db.query(Contact).filter(
                Contact.email == addr,
                Contact.tenant_id == tenant_id,
                Contact.is_deleted == False,
            ).first()

            # 2. Create if missing
            if not contact:
                # Extract root domain
                domain_raw = addr.split("@")[-1] if "@" in addr else None
                ext = tldextract.extract(domain_raw) if domain_raw else None

                organization_id = None
                if ext and ext.domain and ext.suffix:
                    root_domain = f"{ext.domain}.{ext.suffix}"

                    if root_domain not in PUBLIC_DOMAINS:
                        org = self.db.query(Organization).filter(
                            Organization.tenant_id == tenant_id,
                            Organization.is_deleted == False,
                            Organization.website.ilike(f"%{root_domain}%"),
                        ).first()

                        if not org:
                            pretty_name = ext.domain.replace("-", " ").title()
                            org = Organization(name=pretty_name, website=root_domain, tenant_id=tenant_id)
                            try:
                                self.db.add(org)
                                self.db.flush()
                                logger.info("organization_auto_created", domain=root_domain, org_id=org.id)
                            except Exception:
                                self.db.rollback()
                                org = None

                        if org:
                            organization_id = org.id

                # Parse name
                first_name, last_name = "Unknown", ""
                if name:
                    parts = name.strip().split(" ", 1)
                    first_name = parts[0]
                    if len(parts) > 1:
                        last_name = parts[1]

                contact = Contact(
                    first_name=first_name, last_name=last_name,
                    email=addr, organization_id=organization_id,
                    tenant_id=tenant_id,
                )
                try:
                    self.db.add(contact)
                    self.db.flush()
                    logger.info("contact_auto_created", email=addr, contact_id=contact.id)
                except Exception as e:
                    self.db.rollback()
                    logger.error("contact_auto_create_error", email=addr, error=str(e))
                    continue

            # 3. Insert junction row (idempotent check)
            exists = self.db.execute(
                email_contacts.select().where(
                    email_contacts.c.synced_email_id == email.id,
                    email_contacts.c.contact_id == contact.id,
                )
            ).first()

            if not exists:
                self.db.execute(email_contacts.insert().values(
                    synced_email_id=email.id,
                    contact_id=contact.id,
                    role=role,
                ))

            # 4. Backward compat: sender → linked_contact_id
            if role == "from" and not sender_contact:
                sender_contact = contact

        # Set backward-compat FK columns
        if sender_contact:
            email.linked_contact_id = sender_contact.id
            if sender_contact.organization_id:
                email.linked_organization_id = sender_contact.organization_id

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error("email_link_commit_error", email_id=email.id, error=str(e))

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
        """Try to match attendee emails to CRM contacts/organizations, creating if missing."""
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

            if not contact:
                # Auto-create basic contact
                first_name = "Unknown"
                last_name = ""
                name_str = attendee.get("name")
                if name_str:
                    parts = name_str.strip().split(" ", 1)
                    first_name = parts[0]
                    if len(parts) > 1:
                        last_name = parts[1]

                contact = Contact(
                    first_name=first_name,
                    last_name=last_name or "(Auto-created)",
                    email=email_addr,
                    tenant_id=tenant_id
                )
                try:
                    self.db.add(contact)
                    self.db.flush()
                    logger.info("contact_auto_created_from_event", email=email_addr, contact_id=contact.id)
                except Exception as e:
                    self.db.rollback()
                    logger.error("error_auto_creating_contact_from_event", email=email_addr, error=str(e))
                    continue

            if contact:
                event.linked_contact_id = contact.id
                if contact.organization_id:
                    event.linked_organization_id = contact.organization_id
                self.db.commit()
                break  # Link event to the first matched/created contact

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
