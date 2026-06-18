"""Role CRUD routes — pure storage."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.role_repository import RoleRepository
from app.infrastructure.persistence.models.role import Role
from app.presentation.schemas.role_schemas import (
    RoleCreateRequest, RoleUpdateRequest, RoleResponse, RoleListResponse,
    PermissionResponse, AssignPermissionsRequest, AssignRoleRequest, UserRoleResponse,
)

router = APIRouter(prefix="/api/v1/roles")

@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    return [PermissionResponse.model_validate(p) for p in repo.list_permissions()]

@router.get("", response_model=RoleListResponse)
async def list_roles(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    roles = repo.list_roles(current_user["tenant_id"])
    return RoleListResponse(items=[RoleResponse.model_validate(r) for r in roles], total=len(roles))

@router.post("", response_model=RoleResponse, status_code=201)
async def create_role(data: RoleCreateRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    existing = repo.get_role_by_name(data.name, current_user["tenant_id"])
    if existing:
        raise HTTPException(status_code=409, detail=f"Role '{data.name}' already exists")
    role = Role(name=data.name, description=data.description, tenant_id=current_user["tenant_id"], is_system=False)
    return RoleResponse.model_validate(repo.create_role(role))

@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(role_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    role = repo.get_role_by_id(role_id, current_user["tenant_id"])
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return RoleResponse.model_validate(role)

@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(role_id: str, data: RoleUpdateRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    role = repo.get_role_by_id(role_id, current_user["tenant_id"])
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if data.name is not None:
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    return RoleResponse.model_validate(repo.update_role(role))

@router.delete("/{role_id}", status_code=204)
async def delete_role(role_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    role = repo.get_role_by_id(role_id, current_user["tenant_id"])
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if not repo.delete_role(role):
        raise HTTPException(status_code=403, detail="Cannot delete system roles")

@router.put("/{role_id}/permissions", response_model=RoleResponse)
async def set_role_permissions(role_id: str, data: AssignPermissionsRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    role = repo.get_role_by_id(role_id, current_user["tenant_id"])
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    repo.set_role_permissions(role_id, data.permission_ids)
    db.refresh(role)
    return RoleResponse.model_validate(role)

@router.get("/users/{user_id}/roles", response_model=UserRoleResponse)
async def get_user_roles(user_id: str, db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    roles = repo.get_user_roles(user_id)
    return UserRoleResponse(user_id=user_id, roles=[RoleResponse.model_validate(r) for r in roles])

@router.get("/users/{user_id}/permissions")
async def get_user_permissions(user_id: str, db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    return {"user_id": user_id, "permissions": repo.get_user_permissions(user_id)}

@router.post("/users/{user_id}/roles", status_code=201)
async def assign_role(user_id: str, data: AssignRoleRequest, db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    repo.assign_role_to_user(user_id, data.role_id)
    return {"message": "Role assigned"}

@router.delete("/users/{user_id}/roles/{role_id}", status_code=204)
async def remove_role(user_id: str, role_id: str, db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    repo.remove_role_from_user(user_id, role_id)
