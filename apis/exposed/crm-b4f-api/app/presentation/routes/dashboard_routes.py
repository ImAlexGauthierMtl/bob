"""CRM dashboard routes — B4F composition across CRM backends."""

from fastapi import APIRouter, Depends, Request

from app.application.services.crm_dashboard_service import CRMDashboardService
from app.infrastructure.clients.crm_clients import (
    activity_client,
    contact_client,
    opportunity_client,
    org_client,
    product_client,
)
from app.middleware.auth import get_current_user


router = APIRouter(prefix="/dashboard")
dashboard_service = CRMDashboardService(
    contact_client=contact_client,
    org_client=org_client,
    opportunity_client=opportunity_client,
    activity_client=activity_client,
    product_client=product_client,
)


@router.get("/summary")
async def get_dashboard_summary(request: Request, user: dict = Depends(get_current_user)):
    return await dashboard_service.build_summary(user, forward_headers=request.headers)
