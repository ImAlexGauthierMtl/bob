"""Usage routes — proxies to usage~backend-api."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.infrastructure.clients.platform_clients import usage_client
from app.middleware.auth import get_current_user

router = APIRouter()


# ── Tenant self-service ───────────────────────────

@router.get("/usage")
async def list_usage(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service_type: Optional[str] = None,
    billing_category: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user: dict = Depends(get_current_user),
):
    return await usage_client.list(
        skip, limit, service_type, billing_category, user_id, date_from, date_to,
        forward_headers=request.headers,
    )


@router.get("/usage/summary")
async def get_usage_summary(
    request: Request,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user: dict = Depends(get_current_user),
):
    return await usage_client.get_summary(date_from, date_to, forward_headers=request.headers)


# ── Admin cross-tenant ────────────────────────────

@router.get("/admin/usage")
async def admin_list_usage(
    request: Request,
    tenant_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service_type: Optional[str] = None,
    billing_category: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user: dict = Depends(get_current_user),
):
    return await usage_client.admin_list(
        tenant_id, skip, limit, service_type, billing_category, user_id, date_from, date_to,
        forward_headers=request.headers,
    )


@router.get("/admin/usage/summary")
async def admin_get_usage_summary(
    request: Request,
    tenant_id: str = Query(...),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user: dict = Depends(get_current_user),
):
    return await usage_client.admin_summary(tenant_id, date_from, date_to, forward_headers=request.headers)


@router.get("/admin/usage/by-intent")
async def admin_usage_by_intent(
    request: Request,
    tenant_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    return await usage_client.admin_by_intent(tenant_id, skip, limit, forward_headers=request.headers)


@router.get("/admin/usage/by-intent/{correlation_id}")
async def admin_usage_intent_detail(
    correlation_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    return await usage_client.admin_intent_detail(correlation_id, forward_headers=request.headers)
