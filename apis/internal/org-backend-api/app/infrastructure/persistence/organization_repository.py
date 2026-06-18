"""Organization repository — data access layer."""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.infrastructure.persistence.models.organization import Organization


class OrganizationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, org: Organization) -> Organization:
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        return org

    def get_by_id(self, org_id: str, tenant_id: str) -> Optional[Organization]:
        return self.db.query(Organization).filter(
            Organization.id == org_id,
            Organization.tenant_id == tenant_id,
            Organization.is_deleted == False,
        ).first()

    def list_all(
        self, tenant_id: str, skip: int = 0, limit: int = 50, search: Optional[str] = None,
    ) -> List[Organization]:
        q = self.db.query(Organization).filter(Organization.tenant_id == tenant_id, Organization.is_deleted == False)
        if search:
            q = q.filter(Organization.name.ilike(f"%{search}%"))
        return q.order_by(Organization.name).offset(skip).limit(limit).all()

    def count(self, tenant_id: str) -> int:
        return self.db.query(Organization).filter(
            Organization.tenant_id == tenant_id, Organization.is_deleted == False,
        ).count()

    def update(self, org: Organization) -> Organization:
        org.version += 1
        self.db.commit()
        self.db.refresh(org)
        return org

    def soft_delete(self, org: Organization, deleted_by: str, reason: Optional[str] = None) -> Organization:
        from datetime import datetime, timezone
        org.is_deleted = True
        org.deleted_at = datetime.now(timezone.utc)
        org.deleted_by = deleted_by
        org.deleted_reason = reason
        org.version += 1
        self.db.commit()
        self.db.refresh(org)
        return org
