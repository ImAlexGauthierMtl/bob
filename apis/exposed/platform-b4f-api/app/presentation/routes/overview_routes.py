"""Platform overview routes — B4F composition across platform backends."""

from fastapi import APIRouter, Depends, Request

from app.application.services.platform_overview_service import PlatformOverviewService
from app.infrastructure.clients.platform_clients import usage_client, workflow_client
from app.middleware.auth import get_current_user


router = APIRouter(prefix="/overview")
overview_service = PlatformOverviewService(workflow_client=workflow_client, usage_client=usage_client)


@router.get("")
async def get_platform_overview(request: Request, user: dict = Depends(get_current_user)):
    return await overview_service.build_overview(user, forward_headers=request.headers)
