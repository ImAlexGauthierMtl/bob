"""Usage HTTP routes."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.application.use_cases.usage_use_cases import UsageUseCases
from app.middleware.auth import get_current_user
from app.presentation.deps import get_usage_use_cases
from app.presentation.schemas.usage_schemas import (
    UsageTransactionCreate, UsageTransactionResponse, UsageListResponse,
    UsageSummaryItem, UsageSummaryResponse,
    UsageCorrelationGroupResponse, UsageCorrelationListResponse,
    RateCardCreate, RateCardResponse,
)

router = APIRouter()


# ── Record usage ──────────────────────────────────

@router.post("/api/v1/usage", response_model=UsageTransactionResponse, status_code=status.HTTP_201_CREATED)
async def record_usage(
    data: UsageTransactionCreate,
    user: dict = Depends(get_current_user),
    use_cases: UsageUseCases = Depends(get_usage_use_cases),
):
    created = await use_cases.record_usage(data.model_dump(), user)
    return UsageTransactionResponse.model_validate(created)


# ── List usage ────────────────────────────────────

@router.get("/api/v1/usage", response_model=UsageListResponse)
async def list_usage(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service_type: Optional[str] = None,
    billing_category: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user: dict = Depends(get_current_user),
    use_cases: UsageUseCases = Depends(get_usage_use_cases),
):
    result = await use_cases.list_usage(
        user["tenant_id"],
        skip,
        limit,
        service_type,
        billing_category,
        user_id,
        date_from,
        date_to,
    )
    return UsageListResponse(
        items=[UsageTransactionResponse.model_validate(t) for t in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


# ── Summary ───────────────────────────────────────

@router.get("/api/v1/usage/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user: dict = Depends(get_current_user),
    use_cases: UsageUseCases = Depends(get_usage_use_cases),
):
    result = await use_cases.get_usage_summary(user["tenant_id"], date_from, date_to)
    return UsageSummaryResponse(
        tenant_id=result.tenant_id,
        date_from=result.date_from,
        date_to=result.date_to,
        items=[UsageSummaryItem(**row) for row in result.items],
        total_cogs=result.total_cogs,
        total_transactions=result.total_transactions,
    )


# ── Admin: cross-tenant listing ──────────────────

@router.get("/api/v1/admin/usage", response_model=UsageListResponse)
async def admin_list_usage(
    tenant_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service_type: Optional[str] = None,
    billing_category: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user: dict = Depends(get_current_user),
    use_cases: UsageUseCases = Depends(get_usage_use_cases),
):
    result = await use_cases.list_usage(
        tenant_id,
        skip,
        limit,
        service_type,
        billing_category,
        user_id,
        date_from,
        date_to,
    )
    return UsageListResponse(
        items=[UsageTransactionResponse.model_validate(t) for t in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.get("/api/v1/admin/usage/summary", response_model=UsageSummaryResponse)
async def admin_get_usage_summary(
    tenant_id: str = Query(...),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user: dict = Depends(get_current_user),
    use_cases: UsageUseCases = Depends(get_usage_use_cases),
):
    result = await use_cases.get_usage_summary(tenant_id, date_from, date_to)
    return UsageSummaryResponse(
        tenant_id=result.tenant_id,
        date_from=result.date_from,
        date_to=result.date_to,
        items=[UsageSummaryItem(**row) for row in result.items],
        total_cogs=result.total_cogs,
        total_transactions=result.total_transactions,
    )


# ── Correlation (intent grouping) ────────────────

@router.get("/api/v1/admin/usage/by-intent", response_model=UsageCorrelationListResponse)
async def admin_usage_by_intent(
    tenant_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    use_cases: UsageUseCases = Depends(get_usage_use_cases),
):
    result = await use_cases.list_usage_by_intent(tenant_id, skip, limit)
    return UsageCorrelationListResponse(
        items=[UsageCorrelationGroupResponse(**g) for g in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
        total_cogs=result.total_cogs,
    )


@router.get("/api/v1/admin/usage/by-intent/{correlation_id}", response_model=UsageListResponse)
async def admin_usage_intent_detail(
    correlation_id: str,
    user: dict = Depends(get_current_user),
    use_cases: UsageUseCases = Depends(get_usage_use_cases),
):
    result = await use_cases.list_usage_by_intent_detail(correlation_id)
    return UsageListResponse(
        items=[UsageTransactionResponse.model_validate(t) for t in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


# ── Rate Cards ────────────────────────────────────

@router.get("/api/v1/rate-cards", response_model=list[RateCardResponse])
async def list_rate_cards(
    active_only: bool = Query(True),
    user: dict = Depends(get_current_user),
    use_cases: UsageUseCases = Depends(get_usage_use_cases),
):
    cards = await use_cases.list_rate_cards(active_only)
    return [RateCardResponse.model_validate(c) for c in cards]


@router.post("/api/v1/rate-cards", response_model=RateCardResponse, status_code=status.HTTP_201_CREATED)
async def create_rate_card(
    data: RateCardCreate,
    user: dict = Depends(get_current_user),
    use_cases: UsageUseCases = Depends(get_usage_use_cases),
):
    created = await use_cases.create_rate_card(data.model_dump())
    return RateCardResponse.model_validate(created)
