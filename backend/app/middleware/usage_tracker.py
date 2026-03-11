"""Usage tracker — persistent tracking for all billable platform usage.

Replaces the volatile in-memory CostTracker with a DB-persistent service.
Each API call is logged as a UsageTransaction with COGS calculation.
"""

from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy.orm import Session

from app.domain.entities.usage_transaction import (
    UsageTransaction, ServiceType, BillingCategory, TriggerSource,
)
from app.infrastructure.persistence.usage_repository import (
    UsageRepository, CostRateCardRepository,
)

logger = structlog.get_logger(__name__)


class UsageTracker:
    """Tracks and persists API usage for cost monitoring and billing."""

    def __init__(self, db: Session):
        self.db = db
        self.usage_repo = UsageRepository(db)
        self.rate_repo = CostRateCardRepository(db)

    def _lookup_cogs(
        self,
        provider: str,
        model: str,
        service_type: str,
        unit_type: str,
        quantity: float,
    ) -> Optional[Decimal]:
        """Lookup rate card and calculate COGS."""
        rate = self.rate_repo.get_rate(provider, model, service_type, unit_type)
        if rate is not None:
            return rate * Decimal(str(quantity))
        return None

    def track_llm(
        self,
        *,
        tenant_id: str,
        user_id: str,
        user_email: str = "",
        provider: str = "groq",
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: float = 0.0,
        trigger_source: TriggerSource = TriggerSource.BOB_CHAT,
        trigger_id: str = "",
        correlation_id: str = "",
        correlation_label: str = "",
        is_billable: bool = True,
        metadata: Optional[dict] = None,
    ) -> UsageTransaction:
        """Track an LLM API call."""
        input_cogs = self._lookup_cogs(provider, model, ServiceType.LLM.value, "INPUT_TOKEN", input_tokens) or Decimal("0")
        output_cogs = self._lookup_cogs(provider, model, ServiceType.LLM.value, "OUTPUT_TOKEN", output_tokens) or Decimal("0")
        total_cogs = input_cogs + output_cogs

        txn = UsageTransaction(
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            service_type=ServiceType.LLM,
            provider=provider,
            model=model,
            is_billable=is_billable,
            billing_category=BillingCategory.AI_USAGE,
            trigger_source=trigger_source,
            trigger_id=trigger_id,
            correlation_id=correlation_id,
            correlation_label=correlation_label or None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
            cogs_amount=total_cogs,
            cogs_currency="USD",
            metadata_=metadata,
        )
        self.usage_repo.create(txn)

        logger.info(
            "usage_tracked_llm",
            tenant_id=tenant_id,
            user_id=user_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cogs_usd=float(total_cogs),
            trigger=trigger_source.value if isinstance(trigger_source, TriggerSource) else trigger_source,
            correlation_id=correlation_id,
        )
        return txn

    def track_stt(
        self,
        *,
        tenant_id: str,
        user_id: str,
        user_email: str = "",
        model: str,
        audio_seconds: float,
        duration_ms: float = 0.0,
        trigger_source: TriggerSource = TriggerSource.BOB_VOICE,
        trigger_id: str = "",
        correlation_id: str = "",
        correlation_label: str = "",
        is_billable: bool = True,
        metadata: Optional[dict] = None,
    ) -> UsageTransaction:
        """Track a Speech-to-Text API call."""
        cogs = self._lookup_cogs("groq", model, ServiceType.STT.value, "SECOND", audio_seconds) or Decimal("0")

        txn = UsageTransaction(
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            service_type=ServiceType.STT,
            provider="groq",
            model=model,
            is_billable=is_billable,
            billing_category=BillingCategory.VOICE,
            trigger_source=trigger_source,
            trigger_id=trigger_id,
            correlation_id=correlation_id,
            correlation_label=correlation_label or None,
            audio_seconds=audio_seconds,
            duration_ms=duration_ms,
            cogs_amount=cogs,
            cogs_currency="USD",
            metadata_=metadata,
        )
        self.usage_repo.create(txn)

        logger.info(
            "usage_tracked_stt",
            tenant_id=tenant_id,
            model=model,
            audio_seconds=round(audio_seconds, 1),
            cogs_usd=float(cogs),
        )
        return txn

    def track_tts(
        self,
        *,
        tenant_id: str,
        user_id: str,
        user_email: str = "",
        model: str,
        characters: int,
        duration_ms: float = 0.0,
        provider: str = "groq",
        trigger_source: TriggerSource = TriggerSource.BOB_VOICE,
        trigger_id: str = "",
        correlation_id: str = "",
        correlation_label: str = "",
        is_billable: bool = True,
        metadata: Optional[dict] = None,
    ) -> UsageTransaction:
        """Track a Text-to-Speech API call."""
        cogs = self._lookup_cogs(provider, model, ServiceType.TTS.value, "CHARACTER", characters) or Decimal("0")

        txn = UsageTransaction(
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            service_type=ServiceType.TTS,
            provider=provider,
            model=model,
            is_billable=is_billable,
            billing_category=BillingCategory.VOICE,
            trigger_source=trigger_source,
            trigger_id=trigger_id,
            correlation_id=correlation_id,
            correlation_label=correlation_label or None,
            characters=characters,
            duration_ms=duration_ms,
            cogs_amount=cogs,
            cogs_currency="USD",
            metadata_=metadata,
        )
        self.usage_repo.create(txn)

        logger.info(
            "usage_tracked_tts",
            tenant_id=tenant_id,
            provider=provider,
            model=model,
            characters=characters,
            cogs_usd=float(cogs),
        )
        return txn

    def track_search(
        self,
        *,
        tenant_id: str,
        user_id: str,
        user_email: str = "",
        provider: str = "serper",
        duration_ms: float = 0.0,
        trigger_source: TriggerSource = TriggerSource.ENRICHMENT,
        trigger_id: str = "",
        correlation_id: str = "",
        correlation_label: str = "",
        is_billable: bool = True,
        metadata: Optional[dict] = None,
    ) -> UsageTransaction:
        """Track a search API call (Serper.dev)."""
        cogs = self._lookup_cogs(provider, "google-search", ServiceType.SEARCH.value, "MINUTE", 1) or Decimal("0")

        txn = UsageTransaction(
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            service_type=ServiceType.SEARCH,
            provider=provider,
            model="google-search",
            is_billable=is_billable,
            billing_category=BillingCategory.DATA,
            trigger_source=trigger_source,
            trigger_id=trigger_id,
            correlation_id=correlation_id,
            correlation_label=correlation_label or None,
            duration_ms=duration_ms,
            cogs_amount=cogs,
            cogs_currency="USD",
            metadata_=metadata,
        )
        self.usage_repo.create(txn)

        logger.info(
            "usage_tracked_search",
            tenant_id=tenant_id,
            provider=provider,
            cogs_usd=float(cogs),
        )
        return txn

    def track_tool(
        self,
        *,
        tenant_id: str,
        user_id: str,
        user_email: str = "",
        tool_name: str,
        duration_ms: float = 0.0,
        trigger_source: TriggerSource = TriggerSource.BOB_CHAT,
        trigger_id: str = "",
        correlation_id: str = "",
        correlation_label: str = "",
        is_billable: bool = False,
        metadata: Optional[dict] = None,
    ) -> UsageTransaction:
        """Track a tool execution (typically non-billable, for audit)."""
        txn = UsageTransaction(
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            service_type=ServiceType.TOOL,
            provider="internal",
            model=tool_name,
            is_billable=is_billable,
            billing_category=BillingCategory.AUTOMATION,
            trigger_source=trigger_source,
            trigger_id=trigger_id,
            correlation_id=correlation_id,
            correlation_label=correlation_label or None,
            duration_ms=duration_ms,
            cogs_amount=Decimal("0"),
            cogs_currency="USD",
            metadata_=metadata or {"tool_name": tool_name},
        )
        self.usage_repo.create(txn)

        logger.info(
            "usage_tracked_tool",
            tenant_id=tenant_id,
            tool_name=tool_name,
        )
        return txn

    def track_retrieval(
        self,
        *,
        tenant_id: str,
        user_id: str,
        user_email: str = "",
        query: str,
        chunks_retrieved: int,
        chunks_after_filter: int = 0,
        duration_ms: float = 0.0,
        trigger_source: TriggerSource = TriggerSource.BOB_CHAT,
        trigger_id: str = "",
        correlation_id: str = "",
        correlation_label: str = "",
        is_billable: bool = False,
        metadata: Optional[dict] = None,
    ) -> UsageTransaction:
        """Track a RAG retrieval query (non-billable, for observability)."""
        txn = UsageTransaction(
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            service_type=ServiceType.RETRIEVAL,
            provider="internal",
            model="rag-retriever",
            is_billable=is_billable,
            billing_category=BillingCategory.AI_USAGE,
            trigger_source=trigger_source,
            trigger_id=trigger_id,
            correlation_id=correlation_id,
            correlation_label=correlation_label or None,
            duration_ms=duration_ms,
            cogs_amount=Decimal("0"),
            cogs_currency="USD",
            metadata_=metadata or {
                "query": query[:200],
                "chunks_retrieved": chunks_retrieved,
                "chunks_after_filter": chunks_after_filter,
            },
        )
        self.usage_repo.create(txn)

        logger.info(
            "usage_tracked_retrieval",
            tenant_id=tenant_id,
            query=query[:80],
            chunks=chunks_retrieved,
            correlation_id=correlation_id,
        )
        return txn
