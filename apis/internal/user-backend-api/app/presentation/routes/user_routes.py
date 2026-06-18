"""User CRUD routes — pure storage, no business logic."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.user_repository import UserRepository
from app.infrastructure.persistence.models.user import User
from app.infrastructure.persistence.models.role import UserRole
from app.infrastructure.persistence.role_repository import RoleRepository
from app.events.publishers import publish_user_created, publish_user_updated, publish_user_deleted
from app.presentation.schemas.user_schemas import (
    UserCreateRequest, UserUpdateRequest, UserResponse, UserListResponse,
)

router = APIRouter(prefix="/api/v1/users")


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    users, total = repo.list_by_tenant(current_user["tenant_id"], skip, limit)
    return UserListResponse(items=[UserResponse.model_validate(u) for u in users], total=total, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.get("/by-email/{email}", response_model=UserResponse)
async def get_user_by_email(email: str, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    user = repo.get_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreateRequest, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    existing = repo.get_by_email(data.email.lower())
    if existing:
        raise HTTPException(status_code=409, detail="User with this email already exists")
    user = User(
        email=data.email.lower(),
        password_hash=User.hash_password(data.password),
        first_name=data.first_name, last_name=data.last_name,
        tenant_id=data.tenant_id or "default",
        role=data.role or "member",
        is_super_admin=data.is_super_admin or False,
        job_title=data.job_title, phone=data.phone,
        created_by=data.created_by or "system",
        active_organization_id=data.active_organization_id,
    )
    created = repo.create(user)

    # Assign the matching RBAC role so the user has permissions after login.
    # Without this, get_user_roles() returns [] and every permission-gated
    # API call returns 403 — the user appears to have a "connection problem".
    role_repo = RoleRepository(db)
    role_name = data.role or "member"
    tenant = data.tenant_id or "default"
    matching_role = role_repo.get_role_by_name(role_name, tenant)
    if matching_role:
        existing_user_role = db.query(UserRole).filter(
            UserRole.user_id == created.id, UserRole.role_id == matching_role.id,
        ).first()
        if not existing_user_role:
            db.add(UserRole(user_id=created.id, role_id=matching_role.id))
            db.commit()

    await publish_user_created(created.id, {"email": created.email, "tenant_id": created.tenant_id})
    return UserResponse.model_validate(created)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str, data: UserUpdateRequest,
    current_user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    updates = data.model_dump(exclude_unset=True)
    password_raw = updates.pop("password", None)
    for key, value in updates.items():
        if hasattr(user, key):
            setattr(user, key, value)
    if password_raw:
        user.password_hash = User.hash_password(password_raw)
    user.updated_by = current_user.get("email")
    updated = repo.update(user)
    await publish_user_updated(updated.id, {"email": updated.email, "fields": list(updates.keys())})
    return UserResponse.model_validate(updated)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = UserRepository(db)
    deleted = repo.soft_delete(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    await publish_user_deleted(user_id)


@router.post("/verify-password")
async def verify_password(data: dict, db: Session = Depends(get_db)):
    """Internal endpoint for B4F password verification."""
    repo = UserRepository(db)
    user = repo.get_by_email(data.get("email", "").lower())
    if not user:
        return {"valid": False}
    return {"valid": user.verify_password(data.get("password", ""))}
