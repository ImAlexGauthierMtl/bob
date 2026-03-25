"""User schemas."""
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    tenant_id: Optional[str] = None
    role: Optional[str] = "member"
    job_title: Optional[str] = None
    phone: Optional[str] = None
    created_by: Optional[str] = None
    is_super_admin: Optional[bool] = False
    active_organization_id: Optional[str] = None

class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    role: Optional[str] = None
    active_organization_id: Optional[str] = None
    is_super_admin: Optional[bool] = None
    password: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    job_title: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    role: str = "member"
    is_super_admin: bool = False
    active_organization_id: Optional[str] = None
    trust_score: float = 0.1
    tenant_id: str = "default"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    skip: int = 0
    limit: int = 50
