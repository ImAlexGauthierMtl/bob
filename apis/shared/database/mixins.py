"""Shared SQLAlchemy mixins — reusable across all APIs."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, func


def generate_uuid() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class TenantMixin:
    """Mixin adding tenant_id to every model for multi-tenant isolation."""

    tenant_id = Column(
        String(36),
        nullable=False,
        index=True,
        default="default",
        comment="Tenant identifier for multi-tenant isolation",
    )


class AuditMixin:
    """Mixin adding audit fields (created/updated timestamps and users)."""

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, default=1, nullable=False)


class SoftDeleteMixin:
    """Mixin adding soft-delete fields."""

    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(100), nullable=True)
    deleted_reason = Column(Text, nullable=True)
