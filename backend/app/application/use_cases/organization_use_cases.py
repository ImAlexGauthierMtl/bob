"""Organization use cases — CRUD operations."""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.entities.organization import Organization
from app.infrastructure.persistence.organization_repository import OrganizationRepository


class CreateOrganizationUseCase:
    """Create a new organization."""

    def __init__(self, db: Session):
        self.repo = OrganizationRepository(db)

    def execute(self, tenant_id: str, created_by: str, **kwargs) -> Organization:
        """Create organization with provided fields."""
        org = Organization(
            tenant_id=tenant_id,
            created_by=created_by,
            **kwargs,
        )
        return self.repo.create(org)


class ListOrganizationsUseCase:
    """List organizations with pagination."""

    def __init__(self, db: Session):
        self.repo = OrganizationRepository(db)

    def execute(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> dict:
        """Returns {items: [...], total: int}."""
        items = self.repo.list_all(tenant_id, skip, limit, search)
        total = self.repo.count(tenant_id)
        return {"items": items, "total": total}


class GetOrganizationUseCase:
    """Get a single organization by ID."""

    def __init__(self, db: Session):
        self.repo = OrganizationRepository(db)

    def execute(self, org_id: str, tenant_id: str) -> Optional[Organization]:
        """Returns Organization or None."""
        return self.repo.get_by_id(org_id, tenant_id)


class UpdateOrganizationUseCase:
    """Update an organization."""

    def __init__(self, db: Session):
        self.repo = OrganizationRepository(db)

    def execute(self, org_id: str, tenant_id: str, updated_by: str, **kwargs) -> Optional[Organization]:
        """Update fields on existing organization."""
        org = self.repo.get_by_id(org_id, tenant_id)
        if not org:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(org, key):
                setattr(org, key, value)
        org.updated_by = updated_by
        return self.repo.update(org)


class DeleteOrganizationUseCase:
    """Soft-delete an organization (with child dependency protection)."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = OrganizationRepository(db)

    def execute(self, org_id: str, tenant_id: str, deleted_by: str) -> bool:
        """Returns True if deleted, False if not found. Raises 409 if children exist."""
        from app.middleware.dependency_guard import guard_delete

        org = self.repo.get_by_id(org_id, tenant_id)
        if not org:
            return False
        guard_delete(self.db, "organizations", org_id, tenant_id)
        self.repo.soft_delete(org, deleted_by)
        return True
