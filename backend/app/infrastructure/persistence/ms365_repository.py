"""MS365 repository — data access for connections, emails, events."""

from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.domain.entities.ms365_connection import MS365Connection
from app.domain.entities.synced_email import SyncedEmail
from app.domain.entities.synced_event import SyncedEvent


class MS365Repository:
    """Repository for Microsoft 365 integration data access."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Connection CRUD ──────────────────────────────────────────────

    def create_connection(self, data: dict, tenant_id: str) -> MS365Connection:
        """Create a new MS365 connection for a user."""
        conn = MS365Connection(tenant_id=tenant_id, **data)
        self.db.add(conn)
        self.db.commit()
        self.db.refresh(conn)
        return conn

    def get_connection_by_user(self, user_id: str, tenant_id: str) -> Optional[MS365Connection]:
        """Get active connection for a specific user."""
        return self.db.query(MS365Connection).filter(
            MS365Connection.user_id == user_id,
            MS365Connection.tenant_id == tenant_id,
            MS365Connection.is_deleted == False,
        ).first()

    def get_all_active_connections(self) -> List[MS365Connection]:
        """Get all active connections across tenants for background sync."""
        return self.db.query(MS365Connection).filter(
            MS365Connection.is_active == True,
            MS365Connection.is_deleted == False,
        ).all()

    def update_connection(self, conn: MS365Connection, data: dict) -> MS365Connection:
        """Update fields on a connection."""
        for key, value in data.items():
            if hasattr(conn, key):
                setattr(conn, key, value)
        conn.version += 1
        self.db.commit()
        self.db.refresh(conn)
        return conn

    def soft_delete_connection(self, conn: MS365Connection, deleted_by: str) -> MS365Connection:
        """Soft-delete a connection."""
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
        """Insert or update a synced email (matched by ms_message_id)."""
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
        """Get a specific email by ID for the given user."""
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
    ) -> List[SyncedEmail]:
        """List synced emails for a user with optional filters."""
        query = self.db.query(SyncedEmail).filter(
            SyncedEmail.user_id == user_id,
            SyncedEmail.tenant_id == tenant_id,
        )
        if folder:
            query = query.filter(SyncedEmail.folder == folder)
        if search:
            query = query.filter(SyncedEmail.subject.ilike(f"%{search}%"))
        return query.order_by(desc(SyncedEmail.received_at)).offset(skip).limit(limit).all()

    def count_emails(
        self,
        user_id: str,
        tenant_id: str,
        folder: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        """Count synced emails for a user."""
        query = self.db.query(SyncedEmail).filter(
            SyncedEmail.user_id == user_id,
            SyncedEmail.tenant_id == tenant_id,
        )
        if folder:
            query = query.filter(SyncedEmail.folder == folder)
        if search:
            query = query.filter(SyncedEmail.subject.ilike(f"%{search}%"))
        return query.count()

    # ── Event CRUD ───────────────────────────────────────────────────

    def upsert_event(self, data: dict, tenant_id: str) -> SyncedEvent:
        """Insert or update a synced calendar event (matched by ms_event_id)."""
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
        """Get a specific event by ID for the given user."""
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
        """List synced events for a user with optional date range."""
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
        """Count synced events for a user."""
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
