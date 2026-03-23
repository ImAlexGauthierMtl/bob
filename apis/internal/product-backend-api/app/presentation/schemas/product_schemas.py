"""Product schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ProductCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    category: str = "SOFTWARE"
    unit_price: float = 0
    currency: str = "CAD"
    sku: Optional[str] = None
    is_taxable: bool = True
    tax_rate: Optional[float] = None
    billing_cycle: Optional[str] = None
    contract_term_months: Optional[int] = None
    setup_fee: Optional[float] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[float] = None
    currency: Optional[str] = None
    sku: Optional[str] = None
    is_active: Optional[bool] = None
    is_taxable: Optional[bool] = None
    tax_rate: Optional[float] = None


class ProductResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    unit_price: float
    currency: str
    sku: Optional[str] = None
    is_active: bool
    is_taxable: bool
    tax_rate: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    skip: int
    limit: int
