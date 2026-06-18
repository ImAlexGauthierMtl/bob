"""Role management routes — authorization logic (B4F) + HTTPClient."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.presentation.routes.auth_routes import get_current_user
from app.middleware.authorization import require_role
from app.infrastructure.clients.user_client import role_client
from app.presentation.schemas.role_schemas import (
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse,
    PermissionResponse, AssignPermissionsRequest, AssignRoleRequest, UserRoleResponse,
)

router = APIRouter(prefix="/roles")

@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(request: Request, current_user: dict = Depends(get_current_user)):
    return await role_client.list_permissions(forward_headers=request.headers)

@router.get("", response_model=RoleListResponse)
async def list_roles(request: Request, current_user: dict = Depends(get_current_user)):
    return await role_client.list_roles(forward_headers=request.headers)

@router.post("", response_model=RoleResponse, status_code=201, dependencies=[Depends(require_role("admin"))])
async def create_role(data: RoleCreate, request: Request, current_user: dict = Depends(get_current_user)):
    return await role_client.create_role(data.model_dump(), forward_headers=request.headers)

@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(role_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    role = await role_client.get_role(role_id, forward_headers=request.headers)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role

@router.patch("/{role_id}", response_model=RoleResponse, dependencies=[Depends(require_role("admin"))])
async def update_role(role_id: str, data: RoleUpdate, request: Request, current_user: dict = Depends(get_current_user)):
    return await role_client.update_role(role_id, data.model_dump(exclude_unset=True), forward_headers=request.headers)

@router.delete("/{role_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
async def delete_role(role_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    deleted = await role_client.delete_role(role_id, forward_headers=request.headers)
    if not deleted:
        raise HTTPException(status_code=404, detail="Role not found")

@router.put("/{role_id}/permissions", response_model=RoleResponse, dependencies=[Depends(require_role("admin"))])
async def set_role_permissions(role_id: str, data: AssignPermissionsRequest, request: Request, current_user: dict = Depends(get_current_user)):
    return await role_client.set_permissions(role_id, data.permission_ids, forward_headers=request.headers)

@router.get("/users/{user_id}/roles", response_model=UserRoleResponse)
async def get_user_roles(user_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    roles = await role_client.list_roles(forward_headers=request.headers)
    from app.infrastructure.clients.user_client import user_client
    user_roles = await user_client.get_user_roles(user_id, forward_headers=request.headers)
    return {"user_id": user_id, "roles": user_roles}

@router.post("/users/{user_id}/roles", status_code=201, dependencies=[Depends(require_role("admin"))])
async def assign_role(user_id: str, data: AssignRoleRequest, request: Request, current_user: dict = Depends(get_current_user)):
    await role_client.assign_role(user_id, data.role_id, forward_headers=request.headers)
    return {"message": "Role assigned"}

@router.delete("/users/{user_id}/roles/{role_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
async def remove_role(user_id: str, role_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await role_client.remove_role(user_id, role_id, forward_headers=request.headers)
