"""Pydantic schemas for RBAC routes."""

from typing import Optional, List
from pydantic import BaseModel


class PermissionResponse(BaseModel):
    id: str
    resource: str
    action: str
    description: Optional[str] = None
    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_system: bool
    permissions: List[PermissionResponse] = []
    model_config = {"from_attributes": True}


class RoleListResponse(BaseModel):
    items: List[RoleResponse]
    total: int


class AssignPermissionsRequest(BaseModel):
    permission_ids: List[str]


class AssignRoleRequest(BaseModel):
    role_id: str


class UserRoleResponse(BaseModel):
    user_id: str
    roles: List[RoleResponse]
