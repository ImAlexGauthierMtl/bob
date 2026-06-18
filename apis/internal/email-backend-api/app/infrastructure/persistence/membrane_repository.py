"""Membrane repository — data access for Membrane-backed connections, emails, events."""

from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.infrastructure.persistence.models.membrane_connection import MembraneConnection
from app.infrastructure.persistence.models.membrane_synced_email import MembraneSyncedEmail
from app.infrastructure.persistence.models.membrane_synced_event import MembraneSyncedEvent


class MembraneRepository:
    """Repository for Membrane integration data access."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Connection CRUD ──────────────────────────────────────────────

    def create_connection(self, data: dict, tenant_id: str) -> MembraneConnection:
        conn = MembraneConnection(tenant_id=tenant_id, **data)
        self.db.add(conn)
        self.db.commit()
        self.db.refresh(conn)
        return conn

    def get_connection_by_membrane_id(self, membrane_id: str, tenant_id: str) -> Optional[MembraneConnection]:
        return self.db.query(MembraneConnection).filter(
            MembraneConnection.membrane_connection_id == membrane_id,
            MembraneConnection.tenant_id == tenant_id,
            MembraneConnection.is_deleted == False,
        ).first()

    def get_connection_by_user_integration(
        self, user_id: str, integration_key: str, tenant_id: str
    ) -> Optional[MembraneConnection]:
        return self.db.query(MembraneConnection).filter(
            MembraneConnection.user_id == user_id,
            MembraneConnection.integration_key == integration_key,
            MembraneConnection.tenant_id == tenant_id,
            MembraneConnection.is_deleted == False,
        ).first()

    def get_first_connection_by_user(self, user_id: str, tenant_id: str) -> Optional[MembraneConnection]:
        return self.db.query(MembraneConnection).filter(
            MembraneConnection.user_id == user_id,
            MembraneConnection.tenant_id == tenant_id,
            MembraneConnection.is_deleted == False,
        ).first()

    def get_connection_by_id(self, connection_id: str, tenant_id: str) -> Optional[MembraneConnection]:
        return self.db.query(MembraneConnection).filter(
            MembraneConnection.id == connection_id,
            MembraneConnection.tenant_id == tenant_id,
            MembraneConnection.is_deleted == False,
        ).first()

    def update_connection(self, conn: MembraneConnection, data: dict) -> MembraneConnection:
        for key, value in data.items():
            if hasattr(conn, key):
                setattr(conn, key, value)
        conn.version += 1
        self.db.commit()
        self.db.refresh(conn)
        return conn

    def soft_delete_connection(self, conn: MembraneConnection, deleted_by: str) -> MembraneConnection:
        conn.is_deleted = True
        conn.is_active = False
        conn.deleted_at = datetime.now(timezone.utc)
        conn.deleted_by = deleted_by
        conn.version += 1
        self.db.commit()
        self.db.refresh(conn)
        return conn

    # ── Email CRUD ───────────────────────────────────────────────────

    def upsert_email(self, data: dict, tenant_id: str) -> MembraneSyncedEmail:
        existing = self.db.query(MembraneSyncedEmail).filter(
            MembraneSyncedEmail.provider_message_id == data["provider_message_id"],
        ).first()

        if existing:
            for key, value in data.items():
                if key != "provider_message_id" and hasattr(existing, key):
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        email = MembraneSyncedEmail(tenant_id=tenant_id, **data)
        self.db.add(email)
        self.db.commit()
        self.db.refresh(email)
        return email

    def get_email_by_id(self, email_id: str, user_id: str, tenant_id: str) -> Optional[MembraneSyncedEmail]:
        return self.db.query(MembraneSyncedEmail).filter(
            MembraneSyncedEmail.id == email_id,
            MembraneSyncedEmail.user_id == user_id,
            MembraneSyncedEmail.tenant_id == tenant_id,
        ).first()

    def list_emails(
        self,
        user_id: str,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
        folder: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[MembraneSyncedEmail]:
        query = self.db.query(MembraneSyncedEmail).filter(
            MembraneSyncedEmail.user_id == user_id,
            MembraneSyncedEmail.tenant_id == tenant_id,
        )
        if folder:
            query = query.filter(MembraneSyncedEmail.folder == folder)
        if search:
            query = query.filter(MembraneSyncedEmail.subject.ilike(f"%{search}%"))
        return query.order_by(desc(MembraneSyncedEmail.received_at)).offset(skip).limit(limit).all()

    def count_emails(
        self,
        user_id: str,
        tenant_id: str,
        folder: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        query = self.db.query(MembraneSyncedEmail).filter(
            MembraneSyncedEmail.user_id == user_id,
            MembraneSyncedEmail.tenant_id == tenant_id,
        )
        if folder:
            query = query.filter(MembraneSyncedEmail.folder == folder)
        if search:
            query = query.filter(MembraneSyncedEmail.subject.ilike(f"%{search}%"))
        return query.count()

    # ── Event CRUD ───────────────────────────────────────────────────

    def upsert_event(self, data: dict, tenant_id: str) -> MembraneSyncedEvent:
        existing = self.db.query(MembraneSyncedEvent).filter(
            MembraneSyncedEvent.provider_event_id == data["provider_event_id"],
        ).first()

        if existing:
            for key, value in data.items():
                if key != "provider_event_id" and hasattr(existing, key):
                    setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        event = MembraneSyncedEvent(tenant_id=tenant_id, **data)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_event_by_id(self, event_id: str, user_id: str, tenant_id: str) -> Optional[MembraneSyncedEvent]:
        return self.db.query(MembraneSyncedEvent).filter(
            MembraneSyncedEvent.id == event_id,
            MembraneSyncedEvent.user_id == user_id,
            MembraneSyncedEvent.tenant_id == tenant_id,
        ).first()

    def list_events(
        self,
        user_id: str,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> List[MembraneSyncedEvent]:
        query = self.db.query(MembraneSyncedEvent).filter(
            MembraneSyncedEvent.user_id == user_id,
            MembraneSyncedEvent.tenant_id == tenant_id,
            MembraneSyncedEvent.is_cancelled == False,
        )
        if from_date:
            query = query.filter(MembraneSyncedEvent.start_time >= from_date)
        if to_date:
            query = query.filter(MembraneSyncedEvent.start_time <= to_date)
        return query.order_by(desc(MembraneSyncedEvent.start_time)).offset(skip).limit(limit).all()

    def count_events(
        self,
        user_id: str,
        tenant_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> int:
        query = self.db.query(MembraneSyncedEvent).filter(
            MembraneSyncedEvent.user_id == user_id,
            MembraneSyncedEvent.tenant_id == tenant_id,
            MembraneSyncedEvent.is_cancelled == False,
        )
        if from_date:
            query = query.filter(MembraneSyncedEvent.start_time >= from_date)
        if to_date:
            query = query.filter(MembraneSyncedEvent.start_time <= to_date)
        return query.count()
