"""Product entity."""
import enum
from sqlalchemy import Column, String, Text, Enum as SAEnum, Numeric, Boolean, Integer
from app.infrastructure.persistence.models.base import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class ProductCategory(str, enum.Enum):
    SOFTWARE = "SOFTWARE"
    SERVICE = "SERVICE"
    ADD_ON = "ADD_ON"
    CONSULTING = "CONSULTING"
    HARDWARE = "HARDWARE"


class BillingCycle(str, enum.Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    ANNUAL = "ANNUAL"


class LicenseType(str, enum.Enum):
    PERPETUAL = "PERPETUAL"
    SUBSCRIPTION = "SUBSCRIPTION"
    USAGE_BASED = "USAGE_BASED"


class BillingUnit(str, enum.Enum):
    HOUR = "HOUR"
    DAY = "DAY"
    PROJECT = "PROJECT"
    RETAINER = "RETAINER"


class Product(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "products"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(SAEnum(ProductCategory), nullable=False, default=ProductCategory.SOFTWARE)
    unit_price = Column(Numeric(12, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="CAD")
    sku = Column(String(50), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_taxable = Column(Boolean, default=True, nullable=False)
    tax_rate = Column(Numeric(5, 2), nullable=True)
    min_quantity = Column(Integer, nullable=True, default=1)
    max_quantity = Column(Integer, nullable=True)
    billing_cycle = Column(SAEnum(BillingCycle), nullable=True)
    contract_term_months = Column(Integer, nullable=True)
    auto_renew = Column(Boolean, nullable=True, default=True)
    setup_fee = Column(Numeric(12, 2), nullable=True)
    trial_days = Column(Integer, nullable=True)
    parent_product_id = Column(String(36), nullable=True, index=True)
    is_coterminus = Column(Boolean, nullable=True, default=True)
    license_type = Column(SAEnum(LicenseType), nullable=True)
    max_users = Column(Integer, nullable=True)
    billing_unit = Column(SAEnum(BillingUnit), nullable=True)
    estimated_hours = Column(Numeric(8, 2), nullable=True)
    weight_kg = Column(Numeric(8, 2), nullable=True)
    warranty_months = Column(Integer, nullable=True)
    manufacturer = Column(String(200), nullable=True)
    part_number = Column(String(100), nullable=True)
