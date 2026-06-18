"""Integration Settings routes — per-tenant CRUD for integration configuration.

Admin authorization is enforced BOTH at the B4F layer (communication-b4f-api)
and here via `require_admin` for defense in depth. Mutating routes (POST,
PATCH, DELETE) require signed admin claims in the JWT so this Backend never
calls another Backend over HTTP.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user, require_admin
from app.infrastructure.persistence.integration_settings_repository import IntegrationSettingsRepository
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
    db: Session = Depends(get_db),
):
    """List per-tenant integration settings. Open to any authenticated tenant user."""
    repo = IntegrationSettingsRepository(db)
    items = repo.list_settings(current_user["tenant_id"])
    return IntegrationSettingListResponse(items=[IntegrationSettingResponse.model_validate(i) for i in items])


@router.post("", response_model=IntegrationSettingResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_setting(
    data: IntegrationSettingCreate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create or upsert an integration setting. Admin only."""
    repo = IntegrationSettingsRepository(db)
    setting = repo.upsert_setting(current_user["tenant_id"], data.integration_key, data.model_dump())
    return IntegrationSettingResponse.model_validate(setting)


@router.patch("/{integration_key}", response_model=IntegrationSettingResponse)
async def update_setting(
    integration_key: str,
    data: IntegrationSettingUpdate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update an integration setting. Admin only."""
    repo = IntegrationSettingsRepository(db)
    existing = repo.get_setting(current_user["tenant_id"], integration_key)
    if not existing:
        raise HTTPException(status_code=404, detail="Integration setting not found")
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if hasattr(existing, key) and key not in {"id", "tenant_id", "integration_key", "created_at"}:
            setattr(existing, key, value)
    db.commit()
    db.refresh(existing)
    return IntegrationSettingResponse.model_validate(existing)


@router.delete("/{integration_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    integration_key: str,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete an integration setting. Admin only."""
    repo = IntegrationSettingsRepository(db)
    deleted = repo.delete_setting(current_user["tenant_id"], integration_key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration setting not found")
    return None
