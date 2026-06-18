"""Role HTTP routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from app.application.use_cases.role_use_cases import RoleUseCases
from app.domain.exceptions import RoleAlreadyExistsError, RoleNotFoundError, SystemRoleDeletionError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_role_use_cases
from app.presentation.schemas.role_schemas import (
    RoleCreateRequest, RoleUpdateRequest, RoleResponse, RoleListResponse,
    PermissionResponse, AssignPermissionsRequest, AssignRoleRequest, UserRoleResponse,
)

router = APIRouter(prefix="/api/v1/roles")

@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(use_cases: RoleUseCases = Depends(get_role_use_cases)):
    permissions = await use_cases.list_permissions()
    return [PermissionResponse.model_validate(p) for p in permissions]

@router.get("", response_model=RoleListResponse)
async def list_roles(
    current_user: dict = Depends(get_current_user),
    use_cases: RoleUseCases = Depends(get_role_use_cases),
):
    result = await use_cases.list_roles(current_user["tenant_id"])
    return RoleListResponse(items=[RoleResponse.model_validate(r) for r in result.items], total=result.total)

@router.post("", response_model=RoleResponse, status_code=201)
async def create_role(
    data: RoleCreateRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: RoleUseCases = Depends(get_role_use_cases),
):
    try:
        role = await use_cases.create_role(data.model_dump(), current_user["tenant_id"])
    except RoleAlreadyExistsError:
        raise HTTPException(status_code=409, detail=f"Role '{data.name}' already exists")
    return RoleResponse.model_validate(role)

@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: RoleUseCases = Depends(get_role_use_cases),
):
    try:
        role = await use_cases.get_role(role_id, current_user["tenant_id"])
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="Role not found")
    return RoleResponse.model_validate(role)

@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    data: RoleUpdateRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: RoleUseCases = Depends(get_role_use_cases),
):
    try:
        role = await use_cases.update_role(
            role_id,
            data.model_dump(exclude_unset=True),
            current_user["tenant_id"],
        )
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="Role not found")
    return RoleResponse.model_validate(role)

@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: RoleUseCases = Depends(get_role_use_cases),
):
    try:
        await use_cases.delete_role(role_id, current_user["tenant_id"])
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="Role not found")
    except SystemRoleDeletionError:
        raise HTTPException(status_code=403, detail="Cannot delete system roles")

@router.put("/{role_id}/permissions", response_model=RoleResponse)
async def set_role_permissions(
    role_id: str,
    data: AssignPermissionsRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: RoleUseCases = Depends(get_role_use_cases),
):
    try:
        role = await use_cases.set_role_permissions(
            role_id,
            data.permission_ids,
            current_user["tenant_id"],
        )
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="Role not found")
    return RoleResponse.model_validate(role)

@router.get("/users/{user_id}/roles", response_model=UserRoleResponse)
async def get_user_roles(
    user_id: str,
    use_cases: RoleUseCases = Depends(get_role_use_cases),
):
    roles = await use_cases.get_user_roles(user_id)
    return UserRoleResponse(user_id=user_id, roles=[RoleResponse.model_validate(r) for r in roles])

@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    use_cases: RoleUseCases = Depends(get_role_use_cases),
):
    return {"user_id": user_id, "permissions": await use_cases.get_user_permissions(user_id)}

@router.post("/users/{user_id}/roles", status_code=201)
async def assign_role(
    user_id: str,
    data: AssignRoleRequest,
    use_cases: RoleUseCases = Depends(get_role_use_cases),
):
    return await use_cases.assign_role(user_id, data.role_id)

@router.delete("/users/{user_id}/roles/{role_id}", status_code=204)
async def remove_role(
    user_id: str,
    role_id: str,
    use_cases: RoleUseCases = Depends(get_role_use_cases),
):
    await use_cases.remove_role(user_id, role_id)
