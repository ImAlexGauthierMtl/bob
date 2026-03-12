"""Context Router — Layer 0 of Bob's intelligent model routing.

Single LLM call (Qwen3 32B via Groq, ~100ms) to classify each user
message into a routing category before dispatching to the appropriate
model. Supports sticky routing to maintain context across turns.

Categories:
  - LIGHTWEIGHT: CRM actions, navigation, greetings, simple Q&A → Qwen3 32B
  - STRATEGIC: business advice, market analysis, strategy → Kimi K2.5
  - TECHNICAL: code, SQL, data analysis, statistics → Claude Sonnet
  - PROCEDURE: matches a known BCC procedure → BCC workflow engine
"""

import json
import structlog
from dataclasses import dataclass, field
from typing import Optional

from groq import Groq

from app.config import settings
from app.agents.model_registry import (
    RoutingCategory,
    ModelProfile,
    get_model_for_category,
)

logger = structlog.get_logger(__name__)


# ── Routing result ────────────────────────────────────────────

@dataclass
class RoutingDecision:
    """Result of the context router classification."""

    category: RoutingCategory
    model: ModelProfile
    reason: str = ""
    confidence: float = 1.0


# ── Router LLM tool schema ───────────────────────────────────

ROUTE_TOOL = {
    "type": "function",
    "function": {
        "name": "route",
        "description": (
            "Classify the user's message into a routing category. "
            "Always call this tool with your classification."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["lightweight", "strategic", "technical"],
                    "description": (
                        "The routing category for this message:\n"
                        "- lightweight: CRM actions, navigation, greetings, simple questions, "
                        "data lookups, task management, creating/searching records\n"
                        "- strategic: business advice, market analysis, strategy, competitive "
                        "intelligence, industry trends, executive counsel, investment decisions\n"
                        "- technical: code generation, SQL queries, data analysis, statistics, "
                        "calculations, API design, scripting, debugging, programming"
                    ),
                },
                "reason": {
                    "type": "string",
                    "description": "One-line reason for the classification",
                },
            },
            "required": ["category"],
        },
    },
}


ROUTER_SYSTEM_PROMPT = """\
You are a message router. Your ONLY job is to classify the user's message
into one of three categories by calling the 'route' tool. Do NOT respond
with text — always use the tool.

Categories:
- "lightweight": Simple chat, CRM questions, navigation, greetings, creating
  or searching records, checking pipeline, managing contacts/accounts/opportunities
- "strategic": Business strategy, market analysis, competitive intelligence,
  industry trends, growth advice, investment analysis, executive-level counsel
- "technical": Code, scripts, SQL, data analysis, statistics, calculations,
  API design, debugging, programming tasks

When in doubt between lightweight and strategic, choose lightweight.
When in doubt between lightweight and technical, choose lightweight.
Only choose strategic or technical when the message clearly requires it.

/no_think"""


# ── Sticky routing logic ─────────────────────────────────────

_STICKY_CATEGORIES = {RoutingCategory.STRATEGIC, RoutingCategory.TECHNICAL}
_STICKY_WINDOW = 3  # how many past routing decisions to consider


def _check_sticky_routing(
    session_routing_history: list[str],
) -> Optional[RoutingCategory]:
    """Check if we should maintain the current model due to conversation momentum.

    If the last N routing decisions were all the same high-tier category,
    maintain that routing unless the new message clearly changes topic.

    Args:
        session_routing_history: List of recent routing category values (newest last).

    Returns:
        The sticky category to maintain, or None if no sticky routing applies.
    """
    if not session_routing_history:
        return None

    recent = session_routing_history[-_STICKY_WINDOW:]
    if not recent:
        return None

    # If the last decision was a high-tier category AND it's been consistent
    last = recent[-1]
    try:
        last_cat = RoutingCategory(last)
    except ValueError:
        return None

    if last_cat not in _STICKY_CATEGORIES:
        return None

    # At least 2 of the last 3 must be the same category for sticky to kick in
    count = sum(1 for r in recent if r == last)
    if count >= min(2, len(recent)):
        return last_cat

    return None


# ── Main routing function ────────────────────────────────────

def route_message(
    message: str,
    conversation_history: list[dict] | None = None,
    session_routing_history: list[str] | None = None,
) -> RoutingDecision:
    """Classify a user message into a routing category via micro-classifier LLM.

    Uses a single Qwen3 32B call (~100ms) with forced tool-call for reliable
    parsing. Falls back to LIGHTWEIGHT on any error.

    Args:
        message: The user's current message.
        conversation_history: Last few messages for context.
        session_routing_history: List of past routing category values for
            sticky routing (newest last).

    Returns:
        RoutingDecision with category, model profile, reason, and confidence.
    """
    if not settings.router_enabled:
        return RoutingDecision(
            category=RoutingCategory.LIGHTWEIGHT,
            model=get_model_for_category(RoutingCategory.LIGHTWEIGHT),
            reason="router_disabled",
            confidence=1.0,
        )

    # ── Check sticky routing first (no LLM call needed) ──
    sticky = _check_sticky_routing(session_routing_history or [])

    # ── Build messages for micro-classifier ──
    messages = [{"role": "system", "content": ROUTER_SYSTEM_PROMPT}]

    # Add limited conversation context (last 4 messages max)
    if conversation_history:
        for msg in conversation_history[-4:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")[:300],  # truncate for speed
            })

    messages.append({"role": "user", "content": message})

    try:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model=settings.router_model,
            messages=messages,
            tools=[ROUTE_TOOL],
            tool_choice={"type": "function", "function": {"name": "route"}},
            temperature=0.0,
            max_tokens=settings.router_max_tokens,
        )

        choice = response.choices[0]

        if choice.message.tool_calls:
            tc = choice.message.tool_calls[0]
            args = json.loads(tc.function.arguments)
            raw_category = args.get("category", "lightweight")
            reason = args.get("reason", "")

            try:
                category = RoutingCategory(raw_category)
            except ValueError:
                category = RoutingCategory.LIGHTWEIGHT

            # ── Apply sticky routing ──
            # If the LLM says lightweight but sticky says otherwise,
            # honor sticky unless the LLM explicitly routes to a different
            # high-tier category.
            if (
                sticky
                and category == RoutingCategory.LIGHTWEIGHT
            ):
                category = sticky
                reason = f"sticky_routing({sticky.value}): {reason}"

            model = get_model_for_category(category)

            logger.info(
                "context_routed",
                category=category.value,
                model=model.id,
                reason=reason,
                tokens_in=response.usage.prompt_tokens if response.usage else 0,
                tokens_out=response.usage.completion_tokens if response.usage else 0,
                sticky_applied=bool(sticky and category == sticky),
            )

            return RoutingDecision(
                category=category,
                model=model,
                reason=reason,
                confidence=1.0,
            )

        # No tool call — fallback
        logger.warning(
            "router_no_tool_call",
            content=(choice.message.content or "")[:100],
        )

    except Exception as e:
        error_str = str(e)

        # Try to salvage from failed_generation (same pattern as intent_classifier)
        if "tool_use_failed" in error_str or "failed_generation" in error_str:
            try:
                import re
                fg_match = re.search(
                    r'"category"\s*:\s*"(\w+)"', error_str
                )
                if fg_match:
                    raw = fg_match.group(1)
                    try:
                        category = RoutingCategory(raw)
                    except ValueError:
                        category = RoutingCategory.LIGHTWEIGHT
                    model = get_model_for_category(category)
                    logger.info(
                        "context_routed_from_failed_gen",
                        category=category.value,
                        model=model.id,
                    )
                    return RoutingDecision(
                        category=category,
                        model=model,
                        reason="parsed_from_failed_generation",
                    )
            except Exception:
                pass

        logger.error("context_router_error", error=error_str)

    # ── Ultimate fallback: lightweight ──
    fallback_model = get_model_for_category(RoutingCategory.LIGHTWEIGHT)
    return RoutingDecision(
        category=RoutingCategory.LIGHTWEIGHT,
        model=fallback_model,
        reason="fallback",
        confidence=0.5,
    )
