"""Usage routes — API for viewing platform usage and costs.

Two access levels:
- /api/v1/usage — tenant self-service (own data only)
- /api/v1/admin/usage — super_admin cross-tenant view
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import structlog

from app.infrastructure.database import get_db
from app.infrastructure.persistence.usage_repository import UsageRepository
from app.middleware.auth import get_current_user
from app.presentation.schemas.usage_schemas import (
    UsageTransactionResponse,
    UsageListResponse,
    UsageSummaryItem,
    UsageSummaryResponse,
    UsageCorrelationGroupResponse,
    UsageCorrelationListResponse,
)
from app.domain.entities.user import User

logger = structlog.get_logger(__name__)

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────


def _require_super_admin(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Verify the current user is a super admin."""
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user or not getattr(user, "is_super_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user


# ── Tenant self-service routes ───────────────────────────────


@router.get("/api/v1/usage", response_model=UsageListResponse, tags=["usage"])
async def list_usage(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service_type: Optional[str] = None,
    billing_category: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List usage transactions for the current tenant."""
    repo = UsageRepository(db)
    tenant_id = current_user["tenant_id"]

    items = repo.list_by_tenant(
        tenant_id, skip=skip, limit=limit,
        service_type=service_type, billing_category=billing_category,
        user_id=user_id, date_from=date_from, date_to=date_to,
    )
    total = repo.count_by_tenant(
        tenant_id, service_type=service_type, billing_category=billing_category,
        user_id=user_id, date_from=date_from, date_to=date_to,
    )

    return UsageListResponse(
        items=[UsageTransactionResponse.model_validate(t) for t in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/api/v1/usage/summary", response_model=UsageSummaryResponse, tags=["usage"])
async def get_usage_summary(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get usage summary for the current tenant."""
    repo = UsageRepository(db)
    tenant_id = current_user["tenant_id"]

    summary_rows = repo.get_summary(tenant_id, date_from=date_from, date_to=date_to)

    items = [UsageSummaryItem(**row) for row in summary_rows]
    total_cogs = sum(item.total_cogs for item in items)
    total_txn = sum(item.transaction_count for item in items)

    return UsageSummaryResponse(
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        items=items,
        total_cogs=round(total_cogs, 4),
        total_transactions=total_txn,
    )


# ── Admin cross-tenant routes ───────────────────────────────


@router.get("/api/v1/admin/usage", response_model=UsageListResponse, tags=["usage-admin"])
async def admin_list_usage(
    tenant_id: Optional[str] = Query(None, description="Target tenant ID (omit for all)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service_type: Optional[str] = None,
    billing_category: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    _auth: dict = Depends(_require_super_admin),
    db: Session = Depends(get_db),
):
    """List usage transactions for any tenant (super_admin only)."""
    repo = UsageRepository(db)
    items = repo.list_by_tenant(
        tenant_id, skip=skip, limit=limit,
        service_type=service_type, billing_category=billing_category,
        user_id=user_id, date_from=date_from, date_to=date_to,
    )
    total = repo.count_by_tenant(
        tenant_id, service_type=service_type, billing_category=billing_category,
        user_id=user_id, date_from=date_from, date_to=date_to,
    )
    return UsageListResponse(
        items=[UsageTransactionResponse.model_validate(t) for t in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/api/v1/admin/usage/summary", response_model=UsageSummaryResponse, tags=["usage-admin"])
async def admin_get_usage_summary(
    tenant_id: str = Query(..., description="Target tenant ID"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    _auth: dict = Depends(_require_super_admin),
    db: Session = Depends(get_db),
):
    """Get usage summary for any tenant (super_admin only)."""
    repo = UsageRepository(db)
    summary_rows = repo.get_summary(tenant_id, date_from=date_from, date_to=date_to)

    items = [UsageSummaryItem(**row) for row in summary_rows]
    total_cogs = sum(item.total_cogs for item in items)
    total_txn = sum(item.transaction_count for item in items)

    return UsageSummaryResponse(
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        items=items,
        total_cogs=round(total_cogs, 4),
        total_transactions=total_txn,
    )


@router.get("/api/v1/admin/usage/by-intent", response_model=UsageCorrelationListResponse, tags=["usage-admin"])
async def admin_usage_by_intent(
    tenant_id: Optional[str] = Query(None, description="Target tenant ID (omit for all)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _auth: dict = Depends(_require_super_admin),
    db: Session = Depends(get_db),
):
    """List usage grouped by intent/correlation (super_admin only)."""
    repo = UsageRepository(db)
    groups = repo.list_by_correlation(tenant_id=tenant_id, skip=skip, limit=limit)
    total = repo.count_by_correlation(tenant_id=tenant_id)
    total_cogs = repo.sum_cogs_by_correlation(tenant_id=tenant_id)

    return UsageCorrelationListResponse(
        items=[UsageCorrelationGroupResponse(**g) for g in groups],
        total=total,
        skip=skip,
        limit=limit,
        total_cogs=round(total_cogs, 6),
    )


@router.get("/api/v1/admin/usage/by-intent/{correlation_id}", response_model=UsageListResponse, tags=["usage-admin"])
async def admin_usage_intent_detail(
    correlation_id: str,
    _auth: dict = Depends(_require_super_admin),
    db: Session = Depends(get_db),
):
    """Get all transactions for a given intent/correlation_id (super_admin only)."""
    repo = UsageRepository(db)
    items = repo.list_by_correlation_id(correlation_id)

    return UsageListResponse(
        items=[UsageTransactionResponse.model_validate(t) for t in items],
        total=len(items),
        skip=0,
        limit=len(items),
    )
