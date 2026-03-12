"""Deep Agent LLM client — Claude Sonnet 4.6 via OpenRouter.

Uses the OpenAI-compatible API on OpenRouter to call Anthropic's
Claude Sonnet 4.6 for complex BCC reasoning: supervisor planning,
code generation, safety review, and deployment.
"""

import json
import structlog
from openai import OpenAI

from app.config import settings
from app.infrastructure.provider_resilience import retry_with_backoff

logger = structlog.get_logger(__name__)

DEEP_AGENT_MODEL = "anthropic/claude-sonnet-4.6"

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )
    return _client


@retry_with_backoff(max_retries=2, base_delay=3.0, max_delay=15.0)
def _call_openrouter(
    messages: list[dict],
    system: str | None = None,
    max_tokens: int = 8192,
    tenant_id: str = "",
    user_id: str = "",
    user_email: str = "",
    trigger_source: str = "SYSTEM",
    correlation_id: str = "",
) -> str:
    """Call OpenRouter API with retry."""
    client = _get_client()

    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    response = client.chat.completions.create(
        model=DEEP_AGENT_MODEL,
        messages=full_messages,
        max_tokens=max_tokens,
        temperature=0.3,
    )

    content = response.choices[0].message.content or ""
    usage = response.usage
    tokens_in = usage.prompt_tokens if usage else 0
    tokens_out = usage.completion_tokens if usage else 0

    logger.info(
        "deep_agent_llm_call",
        model=DEEP_AGENT_MODEL,
        input_tokens=tokens_in,
        output_tokens=tokens_out,
    )

    # ── Track usage if tenant context provided ──
    if tenant_id:
        try:
            from app.infrastructure.database import SessionLocal
            from app.middleware.usage_tracker import UsageTracker
            from app.domain.entities.usage_transaction import TriggerSource

            db = SessionLocal()
            try:
                tracker = UsageTracker(db)
                ts = TriggerSource(trigger_source) if trigger_source else TriggerSource.SYSTEM
                tracker.track_llm(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    user_email=user_email,
                    provider="openrouter",
                    model=DEEP_AGENT_MODEL,
                    input_tokens=tokens_in,
                    output_tokens=tokens_out,
                    trigger_source=ts,
                    correlation_id=correlation_id,
                )
                db.commit()
            finally:
                db.close()
        except Exception as track_err:
            logger.warning("openrouter_usage_tracking_failed", error=str(track_err))

    return content


def deep_agent_chat(
    prompt: str,
    system_prompt: str | None = None,
    json_mode: bool = False,
    # ── Usage tracking context ──
    tenant_id: str = "",
    user_id: str = "",
    user_email: str = "",
    trigger_source: str = "SYSTEM",
    correlation_id: str = "",
) -> str:
    """Send a message to the Deep Agent LLM (Claude Sonnet 4.6 via OpenRouter).

    Args:
        prompt: User/task prompt.
        system_prompt: System instructions.
        json_mode: If True, append JSON-only instruction to system prompt.
        tenant_id: Tenant for usage tracking.
        user_id: User for usage tracking.
        trigger_source: Origin (BOB_CHAT, WORKFLOW, etc.)

    Returns:
        Response text (or JSON string if json_mode).
    """
    sys = system_prompt or ""
    if json_mode:
        sys += "\n\nYou MUST respond with valid JSON only. No markdown, no explanation, no text outside the JSON."

    messages = [{"role": "user", "content": prompt}]
    return _call_openrouter(
        messages,
        system=sys if sys else None,
        max_tokens=8192,
        tenant_id=tenant_id,
        user_id=user_id,
        user_email=user_email,
        trigger_source=trigger_source,
        correlation_id=correlation_id,
    )


def deep_agent_chat_json(prompt: str, system_prompt: str | None = None) -> dict:
    """Call the Deep Agent LLM and parse JSON response."""
    raw = deep_agent_chat(prompt, system_prompt=system_prompt, json_mode=True)
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(raw)
