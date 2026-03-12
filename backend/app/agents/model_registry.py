"""Model Registry — centralized model profiles for intelligent routing.

Maps routing categories to LLM model profiles. Each profile describes
the provider, model name, capabilities, and cost tier. Used by the
Context Router (Layer 0) to select the best model per message.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class RoutingCategory(str, Enum):
    """High-level routing categories detected by Layer 0."""

    LIGHTWEIGHT = "lightweight"   # Simple chat, CRM actions, navigation
    STRATEGIC = "strategic"       # Business advice, market analysis, strategy
    TECHNICAL = "technical"       # Code, SQL, data analysis, statistics
    PROCEDURE = "procedure"       # BCC workflow hit — follow the procedure


class CostTier(str, Enum):
    """Cost tier for model usage."""

    FREE = "free"       # Groq (Qwen3 32B) — no per-token cost
    LOW = "low"         # ~$0.50/M tokens
    MEDIUM = "medium"   # ~$3/M tokens
    HIGH = "high"       # ~$15/M tokens


@dataclass(frozen=True)
class ModelProfile:
    """Describes an LLM model available for routing."""

    id: str
    provider: str               # "groq" | "openrouter"
    model_name: str             # Full model identifier for the API
    capabilities: tuple[str, ...] = ()
    cost_tier: CostTier = CostTier.FREE
    context_window: int = 32768
    max_tokens: int = 4096
    temperature: float = 0.3


# ── Model catalog ─────────────────────────────────────────────

QWEN3_32B = ModelProfile(
    id="qwen3-32b",
    provider="groq",
    model_name="qwen/qwen3-32b",
    capabilities=("chat", "tools", "crm"),
    cost_tier=CostTier.FREE,
    context_window=32768,
    max_tokens=2048,
    temperature=0.3,
)

KIMI_K25 = ModelProfile(
    id="kimi-k2.5",
    provider="openrouter",
    model_name="moonshotai/kimi-k2.5",
    capabilities=("chat", "strategy", "web_search", "long_context"),
    cost_tier=CostTier.LOW,
    context_window=131072,
    max_tokens=8192,
    temperature=0.4,
)

CLAUDE_SONNET = ModelProfile(
    id="claude-sonnet",
    provider="openrouter",
    model_name="anthropic/claude-sonnet-4",
    capabilities=("chat", "code", "analysis", "tools"),
    cost_tier=CostTier.MEDIUM,
    context_window=200000,
    max_tokens=8192,
    temperature=0.2,
)

# ── Category → Model mapping ─────────────────────────────────

_CATEGORY_MODEL_MAP: dict[RoutingCategory, ModelProfile] = {
    RoutingCategory.LIGHTWEIGHT: QWEN3_32B,
    RoutingCategory.STRATEGIC: KIMI_K25,
    RoutingCategory.TECHNICAL: CLAUDE_SONNET,
    RoutingCategory.PROCEDURE: QWEN3_32B,  # procedures use BCC workflow engine
}


def get_model_for_category(category: RoutingCategory) -> ModelProfile:
    """Return the ModelProfile assigned to a routing category."""
    profile = _CATEGORY_MODEL_MAP.get(category, QWEN3_32B)
    logger.debug(
        "model_selected",
        category=category.value,
        model=profile.id,
        provider=profile.provider,
    )
    return profile


def get_all_profiles() -> dict[str, ModelProfile]:
    """Return all registered model profiles keyed by id."""
    return {
        QWEN3_32B.id: QWEN3_32B,
        KIMI_K25.id: KIMI_K25,
        CLAUDE_SONNET.id: CLAUDE_SONNET,
    }
