"""User schemas — Pydantic models for user API."""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserUpdateRequest(BaseModel):
    """Update own profile — all fields optional."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    job_title: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=30)
    bio: Optional[str] = None
    location: Optional[str] = Field(None, max_length=150)
    timezone: Optional[str] = Field(None, max_length=50)


class UserCreateByAdminRequest(BaseModel):
    """Create a user — admin action (agent-driven)."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field("member", description="admin | manager | sales_rep | support | member")
    job_title: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=30)


class UserResponse(BaseModel):
    """User response — public fields (no password_hash)."""

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
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated user list."""

    items: list[UserResponse]
    total: int
    skip: int
    limit: int
