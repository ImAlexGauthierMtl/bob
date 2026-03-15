"""Role management routes — CRUD for roles, permissions, assignments."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.middleware.authorization import require_permission, require_role
from app.infrastructure.persistence.role_repository import RoleRepository
from app.domain.entities.role import Role
from app.presentation.schemas.role_schemas import (
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse,
    PermissionResponse, AssignPermissionsRequest, AssignRoleRequest, UserRoleResponse,
)

router = APIRouter(prefix="/api/v1/roles")


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    return [PermissionResponse.model_validate(p) for p in repo.list_permissions()]


@router.get("", response_model=RoleListResponse)
async def list_roles(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    roles = repo.list_roles(current_user["tenant_id"])
    return RoleListResponse(items=[RoleResponse.model_validate(r) for r in roles], total=len(roles))


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_role("admin"))])
async def create_role(data: RoleCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    existing = repo.get_role_by_name(data.name, current_user["tenant_id"])
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Role '{data.name}' already exists")
    role = Role(name=data.name, description=data.description,
                tenant_id=current_user["tenant_id"], is_system=False, created_by=current_user["email"])
    role = repo.create_role(role)
    return RoleResponse.model_validate(role)


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(role_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    role = repo.get_role_by_id(role_id, current_user["tenant_id"])
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return RoleResponse.model_validate(role)


@router.patch("/{role_id}", response_model=RoleResponse, dependencies=[Depends(require_role("admin"))])
async def update_role(role_id: str, data: RoleUpdate,
                      current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    role = repo.get_role_by_id(role_id, current_user["tenant_id"])
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify system roles")
    if data.name is not None:
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    role.updated_by = current_user["email"]
    role = repo.update_role(role)
    return RoleResponse.model_validate(role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role("admin"))])
async def delete_role(role_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    role = repo.get_role_by_id(role_id, current_user["tenant_id"])
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if not repo.delete_role(role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete system roles")


@router.put("/{role_id}/permissions", response_model=RoleResponse, dependencies=[Depends(require_role("admin"))])
async def set_role_permissions(role_id: str, data: AssignPermissionsRequest,
                               current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    role = repo.get_role_by_id(role_id, current_user["tenant_id"])
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify system role permissions")
    repo.set_role_permissions(role_id, data.permission_ids)
    db.refresh(role)
    return RoleResponse.model_validate(role)


@router.get("/users/{user_id}/roles", response_model=UserRoleResponse)
async def get_user_roles(user_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    roles = repo.get_user_roles(user_id)
    return UserRoleResponse(user_id=user_id, roles=[RoleResponse.model_validate(r) for r in roles])


@router.post("/users/{user_id}/roles", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("admin"))])
async def assign_role_to_user(user_id: str, data: AssignRoleRequest,
                               current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    role = repo.get_role_by_id(data.role_id, current_user["tenant_id"])
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    repo.assign_role_to_user(user_id, data.role_id)
    return {"message": "Role assigned"}


@router.delete("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_role("admin"))])
async def remove_role_from_user(user_id: str, role_id: str,
                                 current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RoleRepository(db)
    repo.remove_role_from_user(user_id, role_id)
