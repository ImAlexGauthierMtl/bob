"""Smart Label schemas."""

from pydantic import BaseModel
from typing import Optional, List


class SmartLabelCreate(BaseModel):
    name: str
    color: str = "#000000"
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    prompt_hint: Optional[str] = None
    parent_id: Optional[str] = None


class SmartLabelUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    prompt_hint: Optional[str] = None
    parent_id: Optional[str] = None


class SmartLabelResponse(BaseModel):
    id: str
    name: str
    color: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    prompt_hint: Optional[str] = None
    parent_id: Optional[str] = None
    tenant_id: str = "default"
    model_config = {"from_attributes": True}


class SmartLabelListResponse(BaseModel):
    items: List[SmartLabelResponse]
    total: int
    skip: Optional[int] = 0
    limit: Optional[int] = 50
