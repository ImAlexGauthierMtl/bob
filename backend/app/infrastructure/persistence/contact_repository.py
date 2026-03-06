"""Contact repository — data access layer."""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.entities.contact import Contact


class ContactRepository:
    """Repository for contact data access."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, contact: Contact) -> Contact:
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def get_by_id(self, contact_id: str, tenant_id: str) -> Optional[Contact]:
        return self.db.query(Contact).filter(
            Contact.id == contact_id,
            Contact.tenant_id == tenant_id,
            Contact.is_deleted == False,
        ).first()

    def list_all(self, tenant_id: str, skip: int = 0, limit: int = 50, search: Optional[str] = None, organization_id: Optional[str] = None) -> List[Contact]:
        query = self.db.query(Contact).filter(Contact.tenant_id == tenant_id, Contact.is_deleted == False)
        if search:
            query = query.filter((Contact.first_name.ilike(f"%{search}%")) | (Contact.last_name.ilike(f"%{search}%")))
        if organization_id:
            query = query.filter(Contact.organization_id == organization_id)
        return query.order_by(Contact.last_name, Contact.first_name).offset(skip).limit(limit).all()

    def count(self, tenant_id: str, organization_id: Optional[str] = None) -> int:
        query = self.db.query(Contact).filter(Contact.tenant_id == tenant_id, Contact.is_deleted == False)
        if organization_id:
            query = query.filter(Contact.organization_id == organization_id)
        return query.count()

    def update(self, contact: Contact) -> Contact:
        contact.version += 1
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def soft_delete(self, contact: Contact, deleted_by: str, reason: Optional[str] = None) -> Contact:
        from datetime import datetime, timezone
        contact.is_deleted = True
        contact.deleted_at = datetime.now(timezone.utc)
        contact.deleted_by = deleted_by
        contact.deleted_reason = reason
        contact.version += 1
        self.db.commit()
        self.db.refresh(contact)
        return contact
