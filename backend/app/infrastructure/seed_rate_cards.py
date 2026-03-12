"""Seed cost rate cards — idempotent seeding of Groq pricing.

Two cost concepts:
1. Per-TOKEN rate — Groq published pricing per model (used for COGS)
2. Per-CREDIT rate — Pool purchase price ($375/500k = $0.00075/credit)

The rate cards store per-token rates for accurate COGS calculation.
Pool credit cost is a business metric computed separately.
"""

from datetime import date
from decimal import Decimal

import structlog
from sqlalchemy.orm import Session

from app.domain.entities.usage_transaction import CostRateCard, ServiceType, RateUnitType

logger = structlog.get_logger(__name__)

# ── Pool credit rate (business metric, not stored in rate cards) ──
# $375 / 500k credits = $0.00075/credit
POOL_CREDIT_RATE = Decimal("0.00075")

# ── Groq published per-token pricing (2026-03) ──
# These are the actual per-token costs used for COGS calculation.
# Models listed with both bare name and prefixed name for matching.
RATE_CARDS = [
    # LLM — qwen/qwen3-32b ($0.29/M in, $0.59/M out)
    {"provider": "groq", "model": "qwen/qwen3-32b", "service_type": ServiceType.LLM,
     "unit_type": RateUnitType.INPUT_TOKEN, "rate_per_unit": Decimal("0.29") / 1_000_000},
    {"provider": "groq", "model": "qwen/qwen3-32b", "service_type": ServiceType.LLM,
     "unit_type": RateUnitType.OUTPUT_TOKEN, "rate_per_unit": Decimal("0.59") / 1_000_000},

    # LLM — llama-3.3-70b-versatile ($0.59/M in, $0.79/M out)
    {"provider": "groq", "model": "llama-3.3-70b-versatile", "service_type": ServiceType.LLM,
     "unit_type": RateUnitType.INPUT_TOKEN, "rate_per_unit": Decimal("0.59") / 1_000_000},
    {"provider": "groq", "model": "llama-3.3-70b-versatile", "service_type": ServiceType.LLM,
     "unit_type": RateUnitType.OUTPUT_TOKEN, "rate_per_unit": Decimal("0.79") / 1_000_000},

    # STT — whisper-large-v3-turbo ($0.04/hour)
    {"provider": "groq", "model": "whisper-large-v3-turbo", "service_type": ServiceType.STT,
     "unit_type": RateUnitType.SECOND, "rate_per_unit": Decimal("0.04") / 3600},

    # TTS — playai-tts ($15/M chars)
    {"provider": "groq", "model": "playai-tts", "service_type": ServiceType.TTS,
     "unit_type": RateUnitType.CHARACTER, "rate_per_unit": Decimal("0.015") / 1000},

    # TTS — canopylabs/orpheus-v1-english ($15/M chars)
    {"provider": "groq", "model": "canopylabs/orpheus-v1-english", "service_type": ServiceType.TTS,
     "unit_type": RateUnitType.CHARACTER, "rate_per_unit": Decimal("0.015") / 1000},

    # TTS — DashScope qwen3-tts-flash ($0.10/10k chars = $0.01/1k chars)
    {"provider": "dashscope", "model": "qwen3-tts-flash", "service_type": ServiceType.TTS,
     "unit_type": RateUnitType.CHARACTER, "rate_per_unit": Decimal("0.01") / 1000},

    # TTS — DashScope qwen3-tts-instruct-flash (same pricing as flash)
    {"provider": "dashscope", "model": "qwen3-tts-instruct-flash", "service_type": ServiceType.TTS,
     "unit_type": RateUnitType.CHARACTER, "rate_per_unit": Decimal("0.01") / 1000},

    # Search — serper.dev ($0.001/query approx)
    {"provider": "serper", "model": "google-search", "service_type": ServiceType.SEARCH,
     "unit_type": RateUnitType.MINUTE, "rate_per_unit": Decimal("0.001")},

    # Hunter.io — Domain Search ($0.01/request approx)
    {"provider": "hunter", "model": "domain-search", "service_type": ServiceType.SEARCH,
     "unit_type": RateUnitType.MINUTE, "rate_per_unit": Decimal("0.01")},

    # Hunter.io — Company Enrichment ($0.01/request approx)
    {"provider": "hunter", "model": "company-enrichment", "service_type": ServiceType.SEARCH,
     "unit_type": RateUnitType.MINUTE, "rate_per_unit": Decimal("0.01")},

    # Groq — Compound (web search + LLM, ~$0.05/request approx — use per-token LLM rates)
    {"provider": "groq", "model": "groq/compound", "service_type": ServiceType.LLM,
     "unit_type": RateUnitType.INPUT_TOKEN, "rate_per_unit": Decimal("0.29") / 1_000_000},
    {"provider": "groq", "model": "groq/compound", "service_type": ServiceType.LLM,
     "unit_type": RateUnitType.OUTPUT_TOKEN, "rate_per_unit": Decimal("0.59") / 1_000_000},

    # OpenRouter — Claude Sonnet 4.6 ($3.00/M in, $15.00/M out)
    {"provider": "openrouter", "model": "anthropic/claude-sonnet-4.6", "service_type": ServiceType.LLM,
     "unit_type": RateUnitType.INPUT_TOKEN, "rate_per_unit": Decimal("3.00") / 1_000_000},
    {"provider": "openrouter", "model": "anthropic/claude-sonnet-4.6", "service_type": ServiceType.LLM,
     "unit_type": RateUnitType.OUTPUT_TOKEN, "rate_per_unit": Decimal("15.00") / 1_000_000},
]


def seed_rate_cards(db: Session) -> None:
    """Seed cost rate cards (drops old, reseeds fresh)."""
    existing_count = db.query(CostRateCard).count()
    if existing_count > 0:
        db.query(CostRateCard).delete()
        logger.info("rate_cards_cleared", old_count=existing_count)

    for card_data in RATE_CARDS:
        card = CostRateCard(
            provider=card_data["provider"],
            model=card_data["model"],
            service_type=card_data["service_type"],
            unit_type=card_data["unit_type"],
            rate_per_unit=card_data["rate_per_unit"],
            currency="USD",
            effective_from=date(2026, 3, 1),
        )
        db.add(card)

    db.commit()
    logger.info("rate_cards_seeded", count=len(RATE_CARDS))
