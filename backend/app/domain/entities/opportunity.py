"""Opportunity entity."""

import enum

from sqlalchemy import Column, String, Text, Enum as SAEnum, Float, Date, ForeignKey
from sqlalchemy.orm import relationship

from app.domain.entities.activity import activity_opportunities

from app.domain.entities.base import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class OpportunityStage(str, enum.Enum):
    PROSPECTING = "PROSPECTING"
    QUALIFICATION = "QUALIFICATION"
    PROPOSAL = "PROPOSAL"
    NEGOTIATION = "NEGOTIATION"
    CLOSED_WON = "CLOSED_WON"
    CLOSED_LOST = "CLOSED_LOST"


class OpportunityPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Opportunity(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    """Opportunity entity — sales pipeline deals."""

    __tablename__ = "opportunities"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Core fields
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    stage = Column(SAEnum(OpportunityStage), default=OpportunityStage.PROSPECTING)
    priority = Column(SAEnum(OpportunityPriority), default=OpportunityPriority.MEDIUM)

    # Financial
    amount = Column(Float, nullable=True)
    probability = Column(Float, nullable=True, comment="Win probability 0-100")

    # Dates
    close_date = Column(Date, nullable=True)

    # Source
    source = Column(String(100), nullable=True)

    # FK → Organization
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    organization = relationship("Organization", back_populates="opportunities")

    # FK → Contact (primary contact)
    contact_id = Column(String(36), ForeignKey("contacts.id"), nullable=True, index=True)
    contact = relationship("Contact", back_populates="opportunities")

    # Owner (RBAC)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # Child relations
    quotes = relationship("Quote", back_populates="opportunity", passive_deletes=True)
    products = relationship("OpportunityProduct", back_populates="opportunity", cascade="all, delete-orphan")

    # M:N with Activities
    linked_activities = relationship(
        "Activity",
        secondary=activity_opportunities,
        back_populates="opportunities",
        lazy="selectin"
    )
