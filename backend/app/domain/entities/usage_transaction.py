"""Usage transaction entities — billable usage tracking.

Append-only ledger for all platform usage (LLM, STT, TTS, VoIP, Search,
Enrichment, Workflows, Tools) with tenant isolation and COGS calculation.
"""

import enum
from datetime import date

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, Numeric,
    Date, JSON, Enum as SAEnum, func,
)

from app.domain.entities.base import Base, TenantMixin, generate_uuid


# ── Enums ─────────────────────────────────────────────


class ServiceType(str, enum.Enum):
    """Type of billable service."""

    LLM = "LLM"
    STT = "STT"
    TTS = "TTS"
    VOIP = "VOIP"
    SEARCH = "SEARCH"
    ENRICHMENT = "ENRICHMENT"
    WORKFLOW = "WORKFLOW"
    TOOL = "TOOL"
    RETRIEVAL = "RETRIEVAL"


class BillingCategory(str, enum.Enum):
    """Billing grouping for invoicing."""

    AI_USAGE = "AI_USAGE"
    VOICE = "VOICE"
    DATA = "DATA"
    AUTOMATION = "AUTOMATION"


class TriggerSource(str, enum.Enum):
    """Where in the system the usage originated."""

    BOB_CHAT = "BOB_CHAT"
    BOB_VOICE = "BOB_VOICE"
    WORKFLOW = "WORKFLOW"
    ENRICHMENT = "ENRICHMENT"
    API = "API"
    SYSTEM = "SYSTEM"


class RateUnitType(str, enum.Enum):
    """Unit of measurement for rate cards."""

    INPUT_TOKEN = "INPUT_TOKEN"
    OUTPUT_TOKEN = "OUTPUT_TOKEN"
    SECOND = "SECOND"
    CHARACTER = "CHARACTER"
    MINUTE = "MINUTE"


# ── Entities ──────────────────────────────────────────


class UsageTransaction(Base, TenantMixin):
    """Append-only usage record for a single billable event."""

    __tablename__ = "usage_transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Who
    user_id = Column(String(36), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)

    # When
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # What
    service_type = Column(SAEnum(ServiceType), nullable=False, index=True)
    provider = Column(String(50), nullable=True)   # groq, serper, twilio, openai
    model = Column(String(100), nullable=True)      # qwen3-32b, whisper-v3-turbo, etc.

    # Billing
    is_billable = Column(Boolean, nullable=False, default=True)
    billing_category = Column(SAEnum(BillingCategory), nullable=False, index=True)

    # Origin
    trigger_source = Column(SAEnum(TriggerSource), nullable=False, index=True)
    trigger_id = Column(String(100), nullable=True)      # session_id, workflow_execution_id
    correlation_id = Column(String(36), nullable=True, index=True)  # groups related transactions
    correlation_label = Column(String(255), nullable=True)  # human-readable intent name

    # Metrics — LLM
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)

    # Metrics — Audio
    audio_seconds = Column(Float, nullable=True)

    # Metrics — TTS
    characters = Column(Integer, nullable=True)

    # Metrics — VoIP
    voip_minutes = Column(Float, nullable=True)

    # Cost
    cogs_amount = Column(Numeric(12, 6), nullable=True, comment="Calculated supplier cost")
    cogs_currency = Column(String(3), nullable=False, default="USD")

    # Extensible context
    metadata_ = Column("metadata", JSON, nullable=True, comment="tool_name, skill, step_name, etc.")

    # Duration of the API call itself
    duration_ms = Column(Float, nullable=True)


class CostRateCard(Base):
    """Supplier pricing — historized rate cards for COGS calculation."""

    __tablename__ = "cost_rate_cards"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    provider = Column(String(50), nullable=False, index=True)
    model = Column(String(100), nullable=False, index=True)
    service_type = Column(SAEnum(ServiceType), nullable=False)

    unit_type = Column(SAEnum(RateUnitType), nullable=False)
    rate_per_unit = Column(Numeric(18, 12), nullable=False, comment="Cost per unit in currency")
    currency = Column(String(3), nullable=False, default="USD")

    effective_from = Column(Date, nullable=False, default=date.today)
    effective_to = Column(Date, nullable=True, comment="NULL = currently active")
