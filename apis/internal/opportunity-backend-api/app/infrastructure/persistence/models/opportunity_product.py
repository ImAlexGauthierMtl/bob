"""OpportunityProduct entity."""
from sqlalchemy import Column, String, Integer, Numeric, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.infrastructure.persistence.models.base import Base, TenantMixin, AuditMixin, generate_uuid


class OpportunityProduct(Base, TenantMixin, AuditMixin):
    __tablename__ = "opportunity_products"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    opportunity_id = Column(String(36), ForeignKey("opportunities.id"), nullable=False, index=True)
    product_id = Column(String(36), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False)
    discount_percent = Column(Numeric(5, 2), nullable=True)
    notes = Column(Text, nullable=True)
    opportunity = relationship("Opportunity", back_populates="products")
