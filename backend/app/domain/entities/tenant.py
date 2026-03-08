"""Tenant entity — platform subscriber management."""

import enum

from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, Enum as SAEnum, Boolean

from app.domain.entities.base import Base, AuditMixin, SoftDeleteMixin, generate_uuid


class TenantStatus(str, enum.Enum):
    """Tenant lifecycle status."""

    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"


class TenantPlan(str, enum.Enum):
    """Subscription plan tier."""

    STARTER = "STARTER"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class Tenant(Base, AuditMixin, SoftDeleteMixin):
    """Tenant entity — platform subscribers (no TenantMixin, IS the tenant)."""

    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Identity
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)

    # Subscription
    status = Column(SAEnum(TenantStatus), default=TenantStatus.TRIAL, nullable=False)
    plan = Column(SAEnum(TenantPlan), default=TenantPlan.STARTER, nullable=False)

    # Owner
    owner_email = Column(String(255), nullable=False)
    owner_name = Column(String(255), nullable=False)

    # Limits
    max_users = Column(Integer, default=5, nullable=False)

    # Dates
    subscription_start = Column(DateTime(timezone=True), nullable=True)
    subscription_end = Column(DateTime(timezone=True), nullable=True)

    # Config
    settings = Column(JSON, nullable=True, comment="Tenant-specific configuration")
    notes = Column(Text, nullable=True, comment="Internal admin notes")
