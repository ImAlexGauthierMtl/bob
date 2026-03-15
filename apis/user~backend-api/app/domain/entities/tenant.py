"""Tenant entity."""
import enum
from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, Enum as SAEnum
from app.domain.entities.base import Base, AuditMixin, SoftDeleteMixin, generate_uuid

class TenantStatus(str, enum.Enum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"

class TenantPlan(str, enum.Enum):
    STARTER = "STARTER"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"

class Tenant(Base, AuditMixin, SoftDeleteMixin):
    __tablename__ = "tenants"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    status = Column(SAEnum(TenantStatus), default=TenantStatus.TRIAL, nullable=False)
    plan = Column(SAEnum(TenantPlan), default=TenantPlan.STARTER, nullable=False)
    owner_email = Column(String(255), nullable=False)
    owner_name = Column(String(255), nullable=False)
    max_users = Column(Integer, default=5, nullable=False)
    subscription_start = Column(DateTime(timezone=True), nullable=True)
    subscription_end = Column(DateTime(timezone=True), nullable=True)
    settings = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
