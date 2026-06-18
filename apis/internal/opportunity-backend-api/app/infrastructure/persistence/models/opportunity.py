"""Opportunity entity."""
import enum
from sqlalchemy import Column, String, Text, Enum as SAEnum, Float, Date
from sqlalchemy.orm import relationship
from app.infrastructure.persistence.models.base import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


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
    __tablename__ = "opportunities"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    stage = Column(SAEnum(OpportunityStage), default=OpportunityStage.PROSPECTING)
    priority = Column(SAEnum(OpportunityPriority), default=OpportunityPriority.MEDIUM)
    amount = Column(Float, nullable=True)
    probability = Column(Float, nullable=True)
    close_date = Column(Date, nullable=True)
    source = Column(String(100), nullable=True)
    organization_id = Column(String(36), nullable=True, index=True)
    contact_id = Column(String(36), nullable=True, index=True)
    owner_id = Column(String(36), nullable=True, index=True)
    products = relationship("OpportunityProduct", back_populates="opportunity", cascade="all, delete-orphan")
