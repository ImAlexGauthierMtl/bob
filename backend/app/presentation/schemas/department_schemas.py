"""Department schemas — Pydantic models."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    manager_user_id: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    manager_user_id: Optional[str] = None


class DepartmentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    manager_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DepartmentListResponse(BaseModel):
    items: List[DepartmentResponse]
    total: int
    skip: int
    limit: int


class DepartmentMemberAdd(BaseModel):
    user_id: str
    is_manager: bool = False


class DepartmentMemberResponse(BaseModel):
    user_id: str
    department_id: str
    is_manager: str
