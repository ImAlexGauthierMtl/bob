"""Organization entity."""

import enum

from sqlalchemy import Column, String, Text, Enum as SAEnum, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.domain.entities.activity import activity_organizations

from app.domain.entities.base import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class OrganizationStatus(str, enum.Enum):
    """Organization lifecycle status."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PROSPECT = "PROSPECT"
    CUSTOMER = "CUSTOMER"
    CHURNED = "CHURNED"


class OrganizationType(str, enum.Enum):
    """Organization type."""

    CORPORATION = "CORPORATION"
    SMB = "SMB"
    STARTUP = "STARTUP"
    GOVERNMENT = "GOVERNMENT"
    NONPROFIT = "NONPROFIT"
    OTHER = "OTHER"


class Organization(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    """Organization entity — companies and business entities."""

    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Core fields
    name = Column(String(255), nullable=False, index=True)
    industry = Column(String(100), nullable=True)
    website = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)

    # Address
    address_street = Column(String(255), nullable=True)
    address_city = Column(String(100), nullable=True)
    address_state = Column(String(100), nullable=True)
    address_country = Column(String(100), nullable=True)
    address_postal_code = Column(String(20), nullable=True)

    # Business info
    status = Column(SAEnum(OrganizationStatus), default=OrganizationStatus.PROSPECT)
    org_type = Column(SAEnum(OrganizationType), default=OrganizationType.OTHER)
    employee_count = Column(Integer, nullable=True)
    annual_revenue = Column(Float, nullable=True)
    description = Column(Text, nullable=True)

    # AI enrichment
    ai_enriched = Column(String(1), default="N", comment="Y if enriched by AI agents")
    linkedin_url = Column(String(500), nullable=True)
    logo_url = Column(String(500), nullable=True)
    organization_profile = Column(JSON, nullable=True, comment="Deep enrichment profile (services, contacts, social, etc.)")

    # Bright Data LinkedIn enrichment
    linkedin_followers = Column(Integer, nullable=True, comment="LinkedIn follower count")
    linkedin_employees = Column(Integer, nullable=True, comment="Employees on LinkedIn")
    linkedin_specialties = Column(JSON, nullable=True, comment="LinkedIn specialties/skills")

    # Owner (RBAC)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # Relations
    contacts = relationship("Contact", back_populates="organization", passive_deletes=True)
    opportunities = relationship("Opportunity", back_populates="organization", passive_deletes=True)
    quotes = relationship("Quote", back_populates="organization", passive_deletes=True)

    # M:N with Activities
    linked_activities = relationship(
        "Activity",
        secondary=activity_organizations,
        back_populates="organizations",
        lazy="selectin"
    )
