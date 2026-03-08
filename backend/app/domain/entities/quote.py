"""Quote entity."""

import enum

from sqlalchemy import Column, String, Text, Enum as SAEnum, Float, Date, ForeignKey
from sqlalchemy.orm import relationship

from app.domain.entities.base import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class QuoteStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Quote(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    """Quote entity — pricing proposals for opportunities."""

    __tablename__ = "quotes"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Core fields
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(QuoteStatus), default=QuoteStatus.DRAFT)

    # Financial
    subtotal = Column(Float, default=0.0)
    discount_percent = Column(Float, default=0.0)
    tax_percent = Column(Float, default=0.0)
    total = Column(Float, default=0.0)

    # Dates
    valid_until = Column(Date, nullable=True)

    # Terms
    terms = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # FK → Opportunity
    opportunity_id = Column(String(36), ForeignKey("opportunities.id"), nullable=True, index=True)
    opportunity = relationship("Opportunity", back_populates="quotes")

    # FK → Organization
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    organization = relationship("Organization", back_populates="quotes")

    # Owner (RBAC)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
