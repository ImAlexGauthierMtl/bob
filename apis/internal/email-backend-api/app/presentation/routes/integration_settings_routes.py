"""Integration Settings routes — per-tenant CRUD for integration configuration.

Admin authorization is enforced BOTH at the B4F layer (communication-b4f-api)
and here via `require_admin` for defense in depth. Mutating routes (POST,
PATCH, DELETE) require signed admin claims in the JWT so this Backend never
calls another Backend over HTTP.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.use_cases.integration_settings_use_cases import IntegrationSettingsUseCases
from app.domain.exceptions import IntegrationSettingNotFoundError
from app.middleware.auth import get_current_user, require_admin
from app.presentation.deps import get_integration_settings_use_cases
from app.presentation.schemas.integration_settings_schemas import (
    IntegrationSettingCreate,
    IntegrationSettingUpdate,
    IntegrationSettingResponse,
    IntegrationSettingListResponse,
)

router = APIRouter(prefix="/api/v1/integration-settings")


@router.get("", response_model=IntegrationSettingListResponse)
async def list_settings(
    current_user: dict = Depends(get_current_user),
    use_cases: IntegrationSettingsUseCases = Depends(get_integration_settings_use_cases),
):
    """List per-tenant integration settings. Open to any authenticated tenant user."""
    items = await use_cases.list_settings(current_user["tenant_id"])
    return IntegrationSettingListResponse(items=[IntegrationSettingResponse.model_validate(i) for i in items])


@router.post("", response_model=IntegrationSettingResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_setting(
    data: IntegrationSettingCreate,
    current_user: dict = Depends(require_admin),
    use_cases: IntegrationSettingsUseCases = Depends(get_integration_settings_use_cases),
):
    """Create or upsert an integration setting. Admin only."""
    setting = await use_cases.create_or_update_setting(data.model_dump(), current_user["tenant_id"])
    return IntegrationSettingResponse.model_validate(setting)


@router.patch("/{integration_key}", response_model=IntegrationSettingResponse)
async def update_setting(
    integration_key: str,
    data: IntegrationSettingUpdate,
    current_user: dict = Depends(require_admin),
    use_cases: IntegrationSettingsUseCases = Depends(get_integration_settings_use_cases),
):
    """Update an integration setting. Admin only."""
    try:
        existing = await use_cases.update_setting(
            integration_key,
            data.model_dump(exclude_unset=True),
            current_user["tenant_id"],
        )
    except IntegrationSettingNotFoundError:
        raise HTTPException(status_code=404, detail="Integration setting not found")
    return IntegrationSettingResponse.model_validate(existing)


@router.delete("/{integration_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    integration_key: str,
    current_user: dict = Depends(require_admin),
    use_cases: IntegrationSettingsUseCases = Depends(get_integration_settings_use_cases),
):
    """Delete an integration setting. Admin only."""
    try:
        await use_cases.delete_setting(integration_key, current_user["tenant_id"])
    except IntegrationSettingNotFoundError:
        raise HTTPException(status_code=404, detail="Integration setting not found")
    return None
