"""Smart Label schemas — Pydantic models."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SmartLabelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(..., min_length=1, max_length=20)
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    prompt_hint: Optional[str] = None
    parent_id: Optional[str] = None


class SmartLabelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, min_length=1, max_length=20)
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    prompt_hint: Optional[str] = None
    parent_id: Optional[str] = None


class SmartLabelResponse(BaseModel):
    id: str
    name: str
    color: str
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    prompt_hint: Optional[str] = None
    parent_id: Optional[str] = None
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    
    sub_labels: Optional[List['SmartLabelResponse']] = Field(default_factory=list)

    class Config:
        from_attributes = True


class SmartLabelListResponse(BaseModel):
    items: List[SmartLabelResponse]
    total: int
    skip: int
    limit: int

