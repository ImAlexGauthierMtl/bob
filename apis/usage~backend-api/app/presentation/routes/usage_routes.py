"""Usage CRUD routes — pure storage, no business logic."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.usage_repository import UsageRepository
from app.domain.entities.usage_transaction import UsageTransaction, CostRateCard
from app.events.publishers import publish_usage_recorded
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
    db: Session = Depends(get_db),
):
    repo = UsageRepository(db)
    txn = UsageTransaction(
        tenant_id=user["tenant_id"],
        user_id=data.user_id or user["user_id"],
        user_email=data.user_email or user["email"],
        service_type=data.service_type,
        provider=data.provider,
        model=data.model,
        is_billable=data.is_billable,
        billing_category=data.billing_category,
        trigger_source=data.trigger_source,
        trigger_id=data.trigger_id,
        correlation_id=data.correlation_id,
        correlation_label=data.correlation_label,
        input_tokens=data.input_tokens,
        output_tokens=data.output_tokens,
        audio_seconds=data.audio_seconds,
        characters=data.characters,
        voip_minutes=data.voip_minutes,
        cogs_amount=data.cogs_amount,
        cogs_currency=data.cogs_currency,
        metadata_=data.metadata,
        duration_ms=data.duration_ms,
    )
    created = repo.record(txn)
    await publish_usage_recorded(created.id, {"service_type": data.service_type, "tenant_id": user["tenant_id"]})
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
    db: Session = Depends(get_db),
):
    repo = UsageRepository(db)
    tenant_id = user["tenant_id"]
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


# ── Summary ───────────────────────────────────────

@router.get("/api/v1/usage/summary", response_model=UsageSummaryResponse)
async def get_usage_summary(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = UsageRepository(db)
    tenant_id = user["tenant_id"]
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
    db: Session = Depends(get_db),
):
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


@router.get("/api/v1/admin/usage/summary", response_model=UsageSummaryResponse)
async def admin_get_usage_summary(
    tenant_id: str = Query(...),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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


# ── Correlation (intent grouping) ────────────────

@router.get("/api/v1/admin/usage/by-intent", response_model=UsageCorrelationListResponse)
async def admin_usage_by_intent(
    tenant_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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


@router.get("/api/v1/admin/usage/by-intent/{correlation_id}", response_model=UsageListResponse)
async def admin_usage_intent_detail(
    correlation_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = UsageRepository(db)
    items = repo.list_by_correlation_id(correlation_id)

    return UsageListResponse(
        items=[UsageTransactionResponse.model_validate(t) for t in items],
        total=len(items),
        skip=0,
        limit=len(items),
    )


# ── Rate Cards ────────────────────────────────────

@router.get("/api/v1/rate-cards", response_model=list[RateCardResponse])
async def list_rate_cards(
    active_only: bool = Query(True),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = UsageRepository(db)
    cards = repo.list_rate_cards(active_only)
    return [RateCardResponse.model_validate(c) for c in cards]


@router.post("/api/v1/rate-cards", response_model=RateCardResponse, status_code=status.HTTP_201_CREATED)
async def create_rate_card(
    data: RateCardCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = UsageRepository(db)
    card = CostRateCard(
        provider=data.provider,
        model=data.model,
        service_type=data.service_type,
        unit_type=data.unit_type,
        rate_per_unit=data.rate_per_unit,
        currency=data.currency,
    )
    created = repo.create_rate_card(card)
    return RateCardResponse.model_validate(created)
