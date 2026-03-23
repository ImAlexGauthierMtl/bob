"""Usage schemas — Pydantic models for Usage Backend API."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── Transaction ────────────────────────────────────

class UsageTransactionCreate(BaseModel):
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    service_type: str
    provider: Optional[str] = None
    model: Optional[str] = None
    is_billable: bool = True
    billing_category: str
    trigger_source: str
    trigger_id: Optional[str] = None
    correlation_id: Optional[str] = None
    correlation_label: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    audio_seconds: Optional[float] = None
    characters: Optional[int] = None
    voip_minutes: Optional[float] = None
    cogs_amount: Optional[float] = None
    cogs_currency: str = "USD"
    metadata: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None


class UsageTransactionResponse(BaseModel):
    id: str
    tenant_id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    timestamp: Optional[datetime] = None
    service_type: str
    provider: Optional[str] = None
    model: Optional[str] = None
    is_billable: bool = True
    billing_category: str
    trigger_source: str
    trigger_id: Optional[str] = None
    correlation_id: Optional[str] = None
    correlation_label: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    audio_seconds: Optional[float] = None
    characters: Optional[int] = None
    voip_minutes: Optional[float] = None
    cogs_amount: Optional[float] = None
    cogs_currency: str = "USD"
    duration_ms: Optional[float] = None

    class Config:
        from_attributes = True


class UsageListResponse(BaseModel):
    items: List[UsageTransactionResponse]
    total: int
    skip: int = 0
    limit: int = 50


# ── Summary ────────────────────────────────────────

class UsageSummaryItem(BaseModel):
    service_type: Optional[str] = None
    billing_category: Optional[str] = None
    transaction_count: int = 0
    total_cogs: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0


class UsageSummaryResponse(BaseModel):
    tenant_id: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    items: List[UsageSummaryItem]
    total_cogs: float = 0.0
    total_transactions: int = 0


# ── Correlation ────────────────────────────────────

class UsageCorrelationGroupResponse(BaseModel):
    correlation_id: str
    correlation_label: Optional[str] = None
    transaction_count: int = 0
    total_cogs: float = 0.0
    first_at: Optional[str] = None
    last_at: Optional[str] = None


class UsageCorrelationListResponse(BaseModel):
    items: List[UsageCorrelationGroupResponse]
    total: int
    skip: int = 0
    limit: int = 50
    total_cogs: float = 0.0


# ── Rate Cards ─────────────────────────────────────

class RateCardCreate(BaseModel):
    provider: str
    model: str
    service_type: str
    unit_type: str
    rate_per_unit: float
    currency: str = "USD"
    effective_from: Optional[str] = None


class RateCardResponse(BaseModel):
    id: str
    provider: str
    model: str
    service_type: str
    unit_type: str
    rate_per_unit: float
    currency: str = "USD"
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None

    class Config:
        from_attributes = True
