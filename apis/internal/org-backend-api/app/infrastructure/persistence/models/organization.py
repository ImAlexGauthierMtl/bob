"""Organization entity."""
import enum
from sqlalchemy import Column, String, Text, Enum as SAEnum, Integer, Float, JSON
from app.infrastructure.persistence.models.base import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class OrganizationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PROSPECT = "PROSPECT"
    CUSTOMER = "CUSTOMER"
    CHURNED = "CHURNED"


class OrganizationType(str, enum.Enum):
    CORPORATION = "CORPORATION"
    SMB = "SMB"
    STARTUP = "STARTUP"
    GOVERNMENT = "GOVERNMENT"
    NONPROFIT = "NONPROFIT"
    OTHER = "OTHER"


class Organization(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "organizations"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    industry = Column(String(100), nullable=True)
    website = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address_street = Column(String(255), nullable=True)
    address_city = Column(String(100), nullable=True)
    address_state = Column(String(100), nullable=True)
    address_country = Column(String(100), nullable=True)
    address_postal_code = Column(String(20), nullable=True)
    status = Column(SAEnum(OrganizationStatus), default=OrganizationStatus.PROSPECT)
    org_type = Column(SAEnum(OrganizationType), default=OrganizationType.OTHER)
    employee_count = Column(Integer, nullable=True)
    annual_revenue = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    ai_enriched = Column(String(1), default="N")
    linkedin_url = Column(String(500), nullable=True)
    logo_url = Column(String(500), nullable=True)
    organization_profile = Column(JSON, nullable=True)
    linkedin_followers = Column(Integer, nullable=True)
    linkedin_employees = Column(Integer, nullable=True)
    linkedin_specialties = Column(JSON, nullable=True)
    owner_id = Column(String(36), nullable=True, index=True)
