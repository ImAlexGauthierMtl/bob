"""Authentication schemas — Pydantic models."""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserRegisterRequest(BaseModel):
    """Registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class UserLoginRequest(BaseModel):
    """Login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token pair response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class UserResponse(BaseModel):
    """User response (public fields only)."""

    id: str
    email: str
    first_name: str
    last_name: str
    job_title: str | None = None
    phone: str | None = None
    bio: str | None = None
    location: str | None = None
    timezone: str | None = None
    role: str = "member"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
