"""Quote schemas — Pydantic models."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


class QuoteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = "DRAFT"
    subtotal: Optional[float] = 0.0
    discount_percent: Optional[float] = 0.0
    tax_percent: Optional[float] = 0.0
    total: Optional[float] = 0.0
    valid_until: Optional[date] = None
    terms: Optional[str] = None
    notes: Optional[str] = None
    opportunity_id: Optional[str] = None
    organization_id: Optional[str] = None


class QuoteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    subtotal: Optional[float] = None
    discount_percent: Optional[float] = None
    tax_percent: Optional[float] = None
    total: Optional[float] = None
    valid_until: Optional[date] = None
    terms: Optional[str] = None
    notes: Optional[str] = None
    opportunity_id: Optional[str] = None
    organization_id: Optional[str] = None


class QuoteResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    subtotal: Optional[float] = None
    discount_percent: Optional[float] = None
    tax_percent: Optional[float] = None
    total: Optional[float] = None
    valid_until: Optional[date] = None
    terms: Optional[str] = None
    notes: Optional[str] = None
    opportunity_id: Optional[str] = None
    organization_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QuoteListResponse(BaseModel):
    items: List[QuoteResponse]
    total: int
    skip: int
    limit: int
