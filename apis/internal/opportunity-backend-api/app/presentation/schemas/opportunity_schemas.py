"""Opportunity schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date


class OpportunityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    stage: Optional[str] = "PROSPECTING"
    priority: Optional[str] = "MEDIUM"
    amount: Optional[float] = None
    probability: Optional[float] = None
    close_date: Optional[date] = None
    source: Optional[str] = None
    organization_id: Optional[str] = None
    contact_id: Optional[str] = None


class OpportunityUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    stage: Optional[str] = None
    priority: Optional[str] = None
    amount: Optional[float] = None
    probability: Optional[float] = None
    close_date: Optional[date] = None
    source: Optional[str] = None
    organization_id: Optional[str] = None
    contact_id: Optional[str] = None


class OpportunityResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    stage: Optional[str] = None
    priority: Optional[str] = None
    amount: Optional[float] = None
    probability: Optional[float] = None
    close_date: Optional[date] = None
    source: Optional[str] = None
    organization_id: Optional[str] = None
    contact_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OpportunityListResponse(BaseModel):
    items: List[OpportunityResponse]
    total: int
    skip: int
    limit: int


class OpportunityProductCreate(BaseModel):
    product_id: str
    quantity: int = 1
    unit_price: float
    discount_percent: Optional[float] = None
    notes: Optional[str] = None


class OpportunityProductResponse(BaseModel):
    id: str
    opportunity_id: str
    product_id: str
    quantity: int
    unit_price: float
    discount_percent: Optional[float] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True
