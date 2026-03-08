"""Pydantic schemas for RBAC routes."""

from typing import Optional, List
from pydantic import BaseModel


class PermissionResponse(BaseModel):
    """Permission output schema."""
    id: str
    resource: str
    action: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    """Create role input."""
    name: str
    description: Optional[str] = None


class RoleUpdate(BaseModel):
    """Update role input."""
    name: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(BaseModel):
    """Role output schema."""
    id: str
    name: str
    description: Optional[str] = None
    is_system: bool
    permissions: List[PermissionResponse] = []

    model_config = {"from_attributes": True}


class RoleListResponse(BaseModel):
    """Role list output."""
    items: List[RoleResponse]
    total: int


class AssignPermissionsRequest(BaseModel):
    """Assign permissions to a role."""
    permission_ids: List[str]


class AssignRoleRequest(BaseModel):
    """Assign role to a user."""
    role_id: str


class UserRoleResponse(BaseModel):
    """User role assignment output."""
    user_id: str
    roles: List[RoleResponse]
