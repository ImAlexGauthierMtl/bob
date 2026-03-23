"""MS365 repository — data access for connections, emails, events."""

from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.domain.entities.ms365_connection import MS365Connection
from app.domain.entities.synced_email import SyncedEmail
from app.domain.entities.synced_event import SyncedEvent
from app.domain.entities.email_contact import email_contacts


class MS365Repository:
    """Repository for Microsoft 365 integration data access."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Connection CRUD ──────────────────────────────────────────────

    def create_connection(self, data: dict, tenant_id: str) -> MS365Connection:
        conn = MS365Connection(tenant_id=tenant_id, **data)
        self.db.add(conn)
        self.db.commit()
        self.db.refresh(conn)
        return conn

    def get_connection_by_user(self, user_id: str, tenant_id: str) -> Optional[MS365Connection]:
        return self.db.query(MS365Connection).filter(
            MS365Connection.user_id == user_id,
            MS365Connection.tenant_id == tenant_id,
            MS365Connection.is_deleted == False,
        ).first()

    def get_connection_by_id(self, conn_id: str, tenant_id: str) -> Optional[MS365Connection]:
        return self.db.query(MS365Connection).filter(
            MS365Connection.id == conn_id,
            MS365Connection.tenant_id == tenant_id,
            MS365Connection.is_deleted == False,
        ).first()

    def get_all_active_connections(self) -> List[MS365Connection]:
        return self.db.query(MS365Connection).filter(
            MS365Connection.is_active == True,
            MS365Connection.is_deleted == False,
        ).all()

    def update_connection(self, conn: MS365Connection, data: dict) -> MS365Connection:
        for key, value in data.items():
            if hasattr(conn, key):
                setattr(conn, key, value)
        conn.version += 1
        self.db.commit()
        self.db.refresh(conn)
        return conn

    def soft_delete_connection(self, conn: MS365Connection, deleted_by: str) -> MS365Connection:
        conn.is_deleted = True
        conn.is_active = False
        conn.deleted_at = datetime.now(timezone.utc)
        conn.deleted_by = deleted_by
        conn.version += 1
        self.db.commit()
        self.db.refresh(conn)
        return conn

    # ── Email CRUD ───────────────────────────────────────────────────

    def upsert_email(self, data: dict, tenant_id: str) -> SyncedEmail:
        existing = self.db.query(SyncedEmail).filter(
            SyncedEmail.ms_message_id == data["ms_message_id"],
        ).first()

        if existing:
            for key, value in data.items():
                if key != "ms_message_id" and hasattr(existing, key):
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        email = SyncedEmail(tenant_id=tenant_id, **data)
        self.db.add(email)
        self.db.commit()
        self.db.refresh(email)
        return email

    def get_email_by_id(self, email_id: str, user_id: str, tenant_id: str) -> Optional[SyncedEmail]:
        return self.db.query(SyncedEmail).filter(
            SyncedEmail.id == email_id,
            SyncedEmail.user_id == user_id,
            SyncedEmail.tenant_id == tenant_id,
        ).first()

    def list_emails(
        self,
        user_id: str,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
        folder: Optional[str] = None,
        search: Optional[str] = None,
        linked_contact_id: Optional[str] = None,
        smart_label: Optional[str] = None,
    ) -> List[SyncedEmail]:
        query = self.db.query(SyncedEmail).filter(
            SyncedEmail.user_id == user_id,
            SyncedEmail.tenant_id == tenant_id,
        )
        if folder:
            query = query.filter(SyncedEmail.folder == folder)
        if linked_contact_id:
            query = query.join(
                email_contacts,
                email_contacts.c.synced_email_id == SyncedEmail.id,
            ).filter(email_contacts.c.contact_id == linked_contact_id)
        if search:
            query = query.filter(SyncedEmail.subject.ilike(f"%{search}%"))
        if smart_label:
            query = query.filter(SyncedEmail.smart_label == smart_label)
        return query.order_by(desc(SyncedEmail.received_at)).offset(skip).limit(limit).all()

    def count_emails(
        self,
        user_id: str,
        tenant_id: str,
        folder: Optional[str] = None,
        search: Optional[str] = None,
        linked_contact_id: Optional[str] = None,
        smart_label: Optional[str] = None,
    ) -> int:
        query = self.db.query(SyncedEmail).filter(
            SyncedEmail.user_id == user_id,
            SyncedEmail.tenant_id == tenant_id,
        )
        if folder:
            query = query.filter(SyncedEmail.folder == folder)
        if linked_contact_id:
            query = query.join(
                email_contacts,
                email_contacts.c.synced_email_id == SyncedEmail.id,
            ).filter(email_contacts.c.contact_id == linked_contact_id)
        if search:
            query = query.filter(SyncedEmail.subject.ilike(f"%{search}%"))
        if smart_label:
            query = query.filter(SyncedEmail.smart_label == smart_label)
        return query.count()

    def update_email(self, email: SyncedEmail, data: dict) -> SyncedEmail:
        for key, value in data.items():
            if hasattr(email, key):
                setattr(email, key, value)
        self.db.commit()
        self.db.refresh(email)
        return email

    def delete_email(self, email: SyncedEmail) -> None:
        self.db.delete(email)
        self.db.commit()

    # ── Event CRUD ───────────────────────────────────────────────────

    def upsert_event(self, data: dict, tenant_id: str) -> SyncedEvent:
        existing = self.db.query(SyncedEvent).filter(
            SyncedEvent.ms_event_id == data["ms_event_id"],
        ).first()

        if existing:
            for key, value in data.items():
                if key != "ms_event_id" and hasattr(existing, key):
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        event = SyncedEvent(tenant_id=tenant_id, **data)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_event_by_id(self, event_id: str, user_id: str, tenant_id: str) -> Optional[SyncedEvent]:
        return self.db.query(SyncedEvent).filter(
            SyncedEvent.id == event_id,
            SyncedEvent.user_id == user_id,
            SyncedEvent.tenant_id == tenant_id,
        ).first()

    def list_events(
        self,
        user_id: str,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[SyncedEvent]:
        query = self.db.query(SyncedEvent).filter(
            SyncedEvent.user_id == user_id,
            SyncedEvent.tenant_id == tenant_id,
            SyncedEvent.is_cancelled == False,
        )
        if from_date:
            query = query.filter(SyncedEvent.start_time >= from_date)
        if to_date:
            query = query.filter(SyncedEvent.start_time <= to_date)
        return query.order_by(desc(SyncedEvent.start_time)).offset(skip).limit(limit).all()

    def count_events(
        self,
        user_id: str,
        tenant_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> int:
        query = self.db.query(SyncedEvent).filter(
            SyncedEvent.user_id == user_id,
            SyncedEvent.tenant_id == tenant_id,
            SyncedEvent.is_cancelled == False,
        )
        if from_date:
            query = query.filter(SyncedEvent.start_time >= from_date)
        if to_date:
            query = query.filter(SyncedEvent.start_time <= to_date)
        return query.count()

    def update_event(self, event: SyncedEvent, data: dict) -> SyncedEvent:
        for key, value in data.items():
            if hasattr(event, key):
                setattr(event, key, value)
        self.db.commit()
        self.db.refresh(event)
        return event

    def delete_event(self, event: SyncedEvent) -> None:
        self.db.delete(event)
        self.db.commit()

    # ── Email Contact links ──────────────────────────────────────────

    def link_email_contact(self, synced_email_id: str, contact_id: str, role: str = "from") -> None:
        from shared.database import generate_uuid
        self.db.execute(
            email_contacts.insert().values(
                id=generate_uuid(), synced_email_id=synced_email_id,
                contact_id=contact_id, role=role,
            )
        )
        self.db.commit()

    def unlink_email_contact(self, synced_email_id: str, contact_id: str) -> None:
        self.db.execute(
            email_contacts.delete().where(
                email_contacts.c.synced_email_id == synced_email_id,
                email_contacts.c.contact_id == contact_id,
            )
        )
        self.db.commit()

    def get_email_contacts(self, synced_email_id: str) -> list:
        return self.db.execute(
            email_contacts.select().where(email_contacts.c.synced_email_id == synced_email_id)
        ).fetchall()
