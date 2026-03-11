"""Contact schemas — Pydantic models."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ContactCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = "ACTIVE"
    linkedin_url: Optional[str] = None
    notes: Optional[str] = None
    organization_id: Optional[str] = None


class ContactUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    status: Optional[str] = None
    linkedin_url: Optional[str] = None
    notes: Optional[str] = None
    organization_id: Optional[str] = None


class ContactResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    seniority: Optional[str] = None
    status: Optional[str] = None
    linkedin_url: Optional[str] = None
    headline: Optional[str] = None
    profile_picture_url: Optional[str] = None
    notes: Optional[str] = None
    contact_profile: Optional[dict] = None
    linkedin_followers: Optional[list] = None
    organization_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContactListResponse(BaseModel):
    items: List[ContactResponse]
    total: int
    skip: int
    limit: int
