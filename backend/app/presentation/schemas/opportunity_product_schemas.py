"""Opportunity-Product link schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class OpportunityProductAdd(BaseModel):
    product_id: str
    quantity: int = Field(1, ge=1)
    discount_percent: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


class OpportunityProductResponse(BaseModel):
    id: str
    opportunity_id: str
    product_id: str
    quantity: int
    unit_price: float
    discount_percent: Optional[float] = None
    notes: Optional[str] = None
    # Resolved from product relationship
    product_name: str = ""
    product_category: str = ""
    product_sku: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OpportunityProductListResponse(BaseModel):
    items: List[OpportunityProductResponse]
    total: int
