"""OpportunityProduct entity — line items linking opportunities to products."""

from sqlalchemy import Column, String, Integer, Numeric, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.domain.entities.base import Base, TenantMixin, AuditMixin, generate_uuid


class OpportunityProduct(Base, TenantMixin, AuditMixin):
    """Line item linking an opportunity to a product with quantity and pricing."""

    __tablename__ = "opportunity_products"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    opportunity_id = Column(String(36), ForeignKey("opportunities.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)

    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False, comment="Snapshot of product price at time of linking")
    discount_percent = Column(Numeric(5, 2), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    opportunity = relationship("Opportunity", back_populates="products")
    product = relationship("Product", lazy="joined")
