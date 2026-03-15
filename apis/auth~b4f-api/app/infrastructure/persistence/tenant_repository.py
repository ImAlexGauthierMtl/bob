"""Tenant repository — CRUD operations for platform tenants."""

from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.domain.entities.tenant import Tenant
from shared.infrastructure import get_logger

logger = get_logger(__name__)


class TenantRepository:
    """Repository for Tenant entity — cross-tenant (no tenant_id filter)."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Tenant:
        tenant = Tenant(**kwargs)
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        logger.info("tenant_created", tenant_id=tenant.id, slug=tenant.slug)
        return tenant

    def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        return self.db.query(Tenant).filter(
            Tenant.id == tenant_id, Tenant.is_deleted == False
        ).first()

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        return self.db.query(Tenant).filter(
            Tenant.slug == slug, Tenant.is_deleted == False
        ).first()

    def get_all(
        self, search: Optional[str] = None, status: Optional[str] = None,
        skip: int = 0, limit: int = 50,
    ) -> Tuple[List[Tenant], int]:
        query = self.db.query(Tenant).filter(Tenant.is_deleted == False)
        if search:
            query = query.filter(Tenant.name.ilike(f"%{search}%"))
        if status:
            query = query.filter(Tenant.status == status)
        total = query.count()
        items = query.order_by(Tenant.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def update(self, tenant: Tenant, **kwargs) -> Tenant:
        for key, value in kwargs.items():
            if value is not None:
                setattr(tenant, key, value)
        self.db.commit()
        self.db.refresh(tenant)
        logger.info("tenant_updated", tenant_id=tenant.id)
        return tenant

    def soft_delete(self, tenant: Tenant) -> None:
        tenant.is_deleted = True
        self.db.commit()
        logger.info("tenant_soft_deleted", tenant_id=tenant.id)
