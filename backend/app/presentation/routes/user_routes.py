"""User routes — profile management and team CRUD."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.infrastructure.persistence.user_repository import UserRepository
from app.application.use_cases.user_use_cases import (
    UpdateProfileUseCase,
    ListUsersUseCase,
    CreateUserByAdminUseCase,
)
from app.presentation.schemas.user_schemas import (
    UserUpdateRequest,
    UserCreateByAdminRequest,
    UserResponse,
    UserListResponse,
)

router = APIRouter(prefix="/api/v1/users")


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    data: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's own profile."""
    use_case = UpdateProfileUseCase(db)
    try:
        user = use_case.execute(
            user_id=current_user["user_id"],
            **data.model_dump(exclude_unset=True),
        )
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all users in the tenant."""
    use_case = ListUsersUseCase(db)
    users, total = use_case.execute(
        tenant_id=current_user["tenant_id"],
        skip=skip,
        limit=limit,
    )
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreateByAdminRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new user (admin/agent-driven)."""
    use_case = CreateUserByAdminUseCase(db)
    try:
        user = use_case.execute(
            email=data.email,
            password=data.password,
            first_name=data.first_name,
            last_name=data.last_name,
            tenant_id=current_user["tenant_id"],
            role=data.role,
            job_title=data.job_title,
            phone=data.phone,
            created_by=current_user["email"],
        )
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete a user."""
    if user_id == current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account from this endpoint",
        )
    repo = UserRepository(db)
    deleted = repo.soft_delete(user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return None
