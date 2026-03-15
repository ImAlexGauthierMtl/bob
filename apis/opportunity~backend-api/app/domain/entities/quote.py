"""Quote entity."""
import enum
from sqlalchemy import Column, String, Text, Enum as SAEnum, Float, Date
from app.domain.entities.base import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class QuoteStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Quote(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "quotes"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(QuoteStatus), default=QuoteStatus.DRAFT)
    subtotal = Column(Float, default=0.0)
    discount_percent = Column(Float, default=0.0)
    tax_percent = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    valid_until = Column(Date, nullable=True)
    terms = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    opportunity_id = Column(String(36), nullable=True, index=True)
    organization_id = Column(String(36), nullable=True, index=True)
    owner_id = Column(String(36), nullable=True, index=True)
