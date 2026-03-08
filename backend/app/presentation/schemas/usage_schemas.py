"""Usage schemas — Pydantic models for usage tracking API."""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UsageTransactionResponse(BaseModel):
    """Single usage transaction record."""

    id: str
    tenant_id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    timestamp: datetime
    service_type: str
    provider: Optional[str] = None
    model: Optional[str] = None
    is_billable: bool
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
    metadata_: Optional[dict] = None

    class Config:
        from_attributes = True


class UsageListResponse(BaseModel):
    """Paginated list of usage transactions."""

    items: List[UsageTransactionResponse]
    total: int
    skip: int
    limit: int


class UsageSummaryItem(BaseModel):
    """Aggregated usage for a service_type + billing_category pair."""

    service_type: str
    billing_category: str
    transaction_count: int
    total_cogs: float
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_audio_seconds: float = 0.0
    total_characters: int = 0


class UsageSummaryResponse(BaseModel):
    """Usage summary with breakdown by service type."""

    tenant_id: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    items: List[UsageSummaryItem]
    total_cogs: float
    total_transactions: int


class UsageCorrelationGroupResponse(BaseModel):
    """Grouped usage by correlation_id (intent)."""

    correlation_id: Optional[str] = None
    correlation_label: Optional[str] = None
    transaction_count: int
    total_cogs: float
    first_timestamp: datetime
    service_types: List[str]
    trigger_source: Optional[str] = None
    tenant_id: Optional[str] = None
    user_email: Optional[str] = None


class UsageCorrelationListResponse(BaseModel):
    """Paginated list of correlation groups."""

    items: List[UsageCorrelationGroupResponse]
    total: int
    skip: int
    limit: int
    total_cogs: float
