"""User routes — profile management via user~backend-api."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.presentation.routes.auth_routes import get_current_user
from app.infrastructure.clients.user_client import user_client
from app.presentation.schemas.user_schemas import UserUpdateRequest, UserCreateByAdminRequest, UserResponse, UserListResponse

router = APIRouter(prefix="/users")

@router.put("/me", response_model=UserResponse)
async def update_my_profile(data: UserUpdateRequest, request: Request, current_user: dict = Depends(get_current_user)):
    updated = await user_client.update(current_user["user_id"], data.model_dump(exclude_unset=True), forward_headers=request.headers)
    return updated

@router.get("", response_model=UserListResponse)
async def list_users(skip: int = 0, limit: int = 50, request: Request = None, current_user: dict = Depends(get_current_user)):
    result = await user_client.list_users(skip, limit, forward_headers=request.headers)
    return result

@router.post("", response_model=UserResponse, status_code=201)
async def create_user(data: UserCreateByAdminRequest, request: Request, current_user: dict = Depends(get_current_user)):
    payload = data.model_dump()
    payload["tenant_id"] = current_user["tenant_id"]
    payload["created_by"] = current_user["email"]
    # Inherit the admin's active organization so the new user can navigate
    # the app immediately after login instead of getting stuck on the
    # org-selector page (which requires permissions they may not yet have).
    if not payload.get("active_organization_id"):
        payload["active_organization_id"] = current_user.get("active_organization_id")
    created = await user_client.create(payload, forward_headers=request.headers)
    return created

@router.patch("/{user_id}", response_model=UserResponse)
async def update_user_by_admin(user_id: str, data: UserUpdateRequest, request: Request, current_user: dict = Depends(get_current_user)):
    updated = await user_client.update(user_id, data.model_dump(exclude_unset=True), forward_headers=request.headers)
    return updated

@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    if user_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    deleted = await user_client.delete(user_id, forward_headers=request.headers)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
