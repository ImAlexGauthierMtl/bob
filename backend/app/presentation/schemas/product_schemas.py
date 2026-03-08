"""Product schemas — Pydantic models for enterprise catalog."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ProductCreate(BaseModel):
    # Common
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    category: str = Field("SOFTWARE", pattern="^(SOFTWARE|SERVICE|ADD_ON|CONSULTING|HARDWARE)$")
    unit_price: float = Field(0, ge=0)
    currency: str = Field("CAD", max_length=3)
    sku: Optional[str] = None
    is_active: bool = True
    is_taxable: bool = True
    tax_rate: Optional[float] = None
    min_quantity: Optional[int] = 1
    max_quantity: Optional[int] = None

    # SERVICE / ADD_ON (SaaS)
    billing_cycle: Optional[str] = Field(None, pattern="^(MONTHLY|QUARTERLY|SEMI_ANNUAL|ANNUAL)$")
    contract_term_months: Optional[int] = None
    auto_renew: Optional[bool] = True
    setup_fee: Optional[float] = None
    trial_days: Optional[int] = None

    # ADD_ON only
    parent_product_id: Optional[str] = None
    is_coterminus: Optional[bool] = True

    # SOFTWARE
    license_type: Optional[str] = Field(None, pattern="^(PERPETUAL|SUBSCRIPTION|USAGE_BASED)$")
    max_users: Optional[int] = None

    # CONSULTING
    billing_unit: Optional[str] = Field(None, pattern="^(HOUR|DAY|PROJECT|RETAINER)$")
    estimated_hours: Optional[float] = None

    # HARDWARE
    weight_kg: Optional[float] = None
    warranty_months: Optional[int] = None
    manufacturer: Optional[str] = None
    part_number: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = Field(None, pattern="^(SOFTWARE|SERVICE|ADD_ON|CONSULTING|HARDWARE)$")
    unit_price: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = None
    sku: Optional[str] = None
    is_active: Optional[bool] = None
    is_taxable: Optional[bool] = None
    tax_rate: Optional[float] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    billing_cycle: Optional[str] = None
    contract_term_months: Optional[int] = None
    auto_renew: Optional[bool] = None
    setup_fee: Optional[float] = None
    trial_days: Optional[int] = None
    parent_product_id: Optional[str] = None
    is_coterminus: Optional[bool] = None
    license_type: Optional[str] = None
    max_users: Optional[int] = None
    billing_unit: Optional[str] = None
    estimated_hours: Optional[float] = None
    weight_kg: Optional[float] = None
    warranty_months: Optional[int] = None
    manufacturer: Optional[str] = None
    part_number: Optional[str] = None


class ProductResponse(BaseModel):
    id: str
    # Common
    name: str
    description: Optional[str] = None
    category: str
    unit_price: float
    currency: str = "CAD"
    sku: Optional[str] = None
    is_active: bool
    is_taxable: bool = True
    tax_rate: Optional[float] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    # SaaS
    billing_cycle: Optional[str] = None
    contract_term_months: Optional[int] = None
    auto_renew: Optional[bool] = None
    setup_fee: Optional[float] = None
    trial_days: Optional[int] = None
    # Add-on
    parent_product_id: Optional[str] = None
    is_coterminus: Optional[bool] = None
    # Software
    license_type: Optional[str] = None
    max_users: Optional[int] = None
    # Consulting
    billing_unit: Optional[str] = None
    estimated_hours: Optional[float] = None
    # Hardware
    weight_kg: Optional[float] = None
    warranty_months: Optional[int] = None
    manufacturer: Optional[str] = None
    part_number: Optional[str] = None
    # Audit
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    skip: int
    limit: int
