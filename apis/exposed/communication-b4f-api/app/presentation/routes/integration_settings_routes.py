"""Integration Settings routes — proxy to email-backend-api for tenant admins.

These routes expose per-tenant integration configuration (scope_mode, etc.)
to the frontend so admins can manage how Membrane tenants are scoped.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Optional, List

from app.middleware.auth import get_current_user, require_admin
from app.infrastructure.clients.email_client import integration_settings_client
from app.presentation.schemas.integration_settings_schemas import (
    IntegrationSettingCreate,
    IntegrationSettingUpdate,
    IntegrationSettingResponse,
    IntegrationSettingListResponse,
)

router = APIRouter(prefix="/integration-settings")


@router.get("", response_model=IntegrationSettingListResponse)
async def list_settings(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """List per-tenant integration settings. Read-only: open to any tenant user."""
    items = await integration_settings_client.list(forward_headers=request.headers)
    return IntegrationSettingListResponse(items=items)


@router.post("", response_model=IntegrationSettingResponse, status_code=status.HTTP_201_CREATED)
async def create_setting(
    data: IntegrationSettingCreate,
    request: Request,
    current_user: dict = Depends(require_admin),
):
    """Create or upsert an integration setting. Admin only."""
    result = await integration_settings_client.upsert(data.model_dump(), forward_headers=request.headers)
    return IntegrationSettingResponse.model_validate(result)


@router.patch("/{integration_key}", response_model=IntegrationSettingResponse)
async def update_setting(
    integration_key: str,
    data: IntegrationSettingUpdate,
    request: Request,
    current_user: dict = Depends(require_admin),
):
    """Update an integration setting. Admin only."""
    result = await integration_settings_client.update(integration_key, data.model_dump(exclude_unset=True), forward_headers=request.headers)
    if not result:
        raise HTTPException(status_code=404, detail="Integration setting not found")
    return IntegrationSettingResponse.model_validate(result)


@router.delete("/{integration_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    integration_key: str,
    request: Request,
    current_user: dict = Depends(require_admin),
):
    """Delete an integration setting. Admin only."""
    deleted = await integration_settings_client.delete(integration_key, forward_headers=request.headers)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration setting not found")
    return None
