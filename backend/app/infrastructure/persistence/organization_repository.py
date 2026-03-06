"""Organization repository — data access layer."""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.entities.organization import Organization


class OrganizationRepository:
    """Repository for organization data access."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, org: Organization) -> Organization:
        """Create a new organization."""
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        return org

    def get_by_id(self, org_id: str, tenant_id: str) -> Optional[Organization]:
        """Get organization by ID (tenant-scoped)."""
        return self.db.query(Organization).filter(
            Organization.id == org_id,
            Organization.tenant_id == tenant_id,
            Organization.is_deleted == False,
        ).first()

    def list_all(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> List[Organization]:
        """List organizations with pagination (tenant-scoped)."""
        query = self.db.query(Organization).filter(
            Organization.tenant_id == tenant_id,
            Organization.is_deleted == False,
        )
        if search:
            query = query.filter(Organization.name.ilike(f"%{search}%"))
        return query.order_by(Organization.name).offset(skip).limit(limit).all()

    def count(self, tenant_id: str) -> int:
        """Count organizations (tenant-scoped)."""
        return self.db.query(Organization).filter(
            Organization.tenant_id == tenant_id,
            Organization.is_deleted == False,
        ).count()

    def update(self, org: Organization) -> Organization:
        """Update an organization."""
        org.version += 1
        self.db.commit()
        self.db.refresh(org)
        return org

    def soft_delete(self, org: Organization, deleted_by: str, reason: Optional[str] = None) -> Organization:
        """Soft delete an organization."""
        from datetime import datetime, timezone

        org.is_deleted = True
        org.deleted_at = datetime.now(timezone.utc)
        org.deleted_by = deleted_by
        org.deleted_reason = reason
        org.version += 1
        self.db.commit()
        self.db.refresh(org)
        return org
