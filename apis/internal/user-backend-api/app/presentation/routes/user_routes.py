"""User HTTP routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.application.use_cases.user_use_cases import UserUseCases
from app.domain.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_user_use_cases
from app.presentation.schemas.user_schemas import (
    UserCreateRequest, UserUpdateRequest, UserResponse, UserListResponse,
)

router = APIRouter(prefix="/api/v1/users")


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    result = await use_cases.list_users(current_user["tenant_id"], skip, limit)
    return UserListResponse(
        items=[UserResponse.model_validate(user) for user in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    try:
        user = await use_cases.get_user(user_id)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.get("/by-email/{email}", response_model=UserResponse)
async def get_user_by_email(
    email: str,
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    try:
        user = await use_cases.get_user_by_email(email)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreateRequest,
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    try:
        created = await use_cases.create_user(data.model_dump())
    except UserAlreadyExistsError:
        raise HTTPException(status_code=409, detail="User with this email already exists")
    return UserResponse.model_validate(created)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str, data: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    try:
        updated = await use_cases.update_user(
            user_id,
            data.model_dump(exclude_unset=True),
            current_user,
        )
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(updated)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    try:
        await use_cases.delete_user(user_id)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.post("/verify-password")
async def verify_password(
    data: dict,
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    """Internal endpoint for B4F password verification."""
    return await use_cases.verify_password(data.get("email", ""), data.get("password", ""))
