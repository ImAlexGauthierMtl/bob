"""Integration overview routes — B4F composition for communication settings."""

from fastapi import APIRouter, Depends, Request

from app.application.services.integration_overview_service import IntegrationOverviewService
from app.infrastructure.clients.email_client import (
    connection_client,
    integration_settings_client,
    membrane_crud_client,
    smart_label_client,
)
from app.middleware.auth import get_current_user


router = APIRouter(prefix="/integrations")
overview_service = IntegrationOverviewService(
    integration_settings_client=integration_settings_client,
    connection_client=connection_client,
    membrane_crud_client=membrane_crud_client,
    smart_label_client=smart_label_client,
)


@router.get("/overview")
async def get_integrations_overview(request: Request, current_user: dict = Depends(get_current_user)):
    return await overview_service.build_overview(current_user, forward_headers=request.headers)
