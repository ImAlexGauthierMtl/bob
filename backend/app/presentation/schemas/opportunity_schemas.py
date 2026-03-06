"""Opportunity schemas — Pydantic models."""

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
