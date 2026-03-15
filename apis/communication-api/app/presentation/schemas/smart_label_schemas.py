"""Smart Label schemas."""

from pydantic import BaseModel
from typing import Optional, List


class SmartLabelCreate(BaseModel):
    """Create a smart label."""
    name: str
    color: str = "#000000"
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    prompt_hint: Optional[str] = None
    parent_id: Optional[str] = None


class SmartLabelUpdate(BaseModel):
    """Update a smart label."""
    name: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    prompt_hint: Optional[str] = None
    parent_id: Optional[str] = None


class SmartLabelResponse(BaseModel):
    """A smart label."""
    id: str
    name: str
    color: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    prompt_hint: Optional[str] = None
    parent_id: Optional[str] = None
    
    class Config:
        from_attributes = True


class SmartLabelListResponse(BaseModel):
    """List of smart labels."""
    items: List[SmartLabelResponse]
    total: int
    skip: Optional[int] = 0
    limit: Optional[int] = 50
