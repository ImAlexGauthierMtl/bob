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

from app.infrastructure.persistence.models.base import Base, TenantMixin, generate_uuid


class ServiceType(str, enum.Enum):
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
    AI_USAGE = "AI_USAGE"
    VOICE = "VOICE"
    DATA = "DATA"
    AUTOMATION = "AUTOMATION"


class TriggerSource(str, enum.Enum):
    BOB_CHAT = "BOB_CHAT"
    BOB_VOICE = "BOB_VOICE"
    WORKFLOW = "WORKFLOW"
    ENRICHMENT = "ENRICHMENT"
    API = "API"
    SYSTEM = "SYSTEM"


class RateUnitType(str, enum.Enum):
    INPUT_TOKEN = "INPUT_TOKEN"
    OUTPUT_TOKEN = "OUTPUT_TOKEN"
    SECOND = "SECOND"
    CHARACTER = "CHARACTER"
    MINUTE = "MINUTE"


class UsageTransaction(Base, TenantMixin):
    """Append-only usage record for a single billable event."""

    __tablename__ = "usage_transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    user_id = Column(String(36), nullable=True, index=True)
    user_email = Column(String(255), nullable=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    service_type = Column(SAEnum(ServiceType), nullable=False, index=True)
    provider = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)

    is_billable = Column(Boolean, nullable=False, default=True)
    billing_category = Column(SAEnum(BillingCategory), nullable=False, index=True)

    trigger_source = Column(SAEnum(TriggerSource), nullable=False, index=True)
    trigger_id = Column(String(100), nullable=True)
    correlation_id = Column(String(36), nullable=True, index=True)
    correlation_label = Column(String(255), nullable=True)

    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)

    audio_seconds = Column(Float, nullable=True)
    characters = Column(Integer, nullable=True)
    voip_minutes = Column(Float, nullable=True)

    cogs_amount = Column(Numeric(12, 6), nullable=True, comment="Calculated supplier cost")
    cogs_currency = Column(String(3), nullable=False, default="USD")

    metadata_ = Column("metadata", JSON, nullable=True, comment="tool_name, skill, step_name, etc.")

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
