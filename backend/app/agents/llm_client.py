"""Groq LLM client — reusable wrapper with retry resilience.

UNRULED PATTERN — No HDQ template exists for LLM client integration.
"""

from typing import Optional

from groq import Groq
import structlog

from app.config import settings
from app.infrastructure.provider_resilience import retry_with_backoff

logger = structlog.get_logger(__name__)


class LLMClient:
    """Client for Groq API — chat completions with JSON mode support."""

    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.default_model = settings.groq_default_model

    @retry_with_backoff(max_retries=2, base_delay=1.0, max_delay=3.0)
    def _call_with_retry(self, **kwargs):
        return self.client.chat.completions.create(**kwargs)

    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        # ── Usage tracking context (optional) ──
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        trigger_source: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """Send a chat completion request to Groq.

        Args:
            prompt: User message
            system_prompt: System message (optional)
            model: Model override (defaults to settings)
            json_mode: Enable JSON response format
            temperature: Creativity (0.0-1.0)
            max_tokens: Max response tokens
            tenant_id: Tenant for usage tracking
            user_id: User for usage tracking
            user_email: User email for usage tracking
            trigger_source: Origin (BOB_CHAT, WORKFLOW, etc.)
            correlation_id: Groups related transactions

        Returns:
            Response text content
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self._call_with_retry(**kwargs)
            content = response.choices[0].message.content or ""
            tokens_in = response.usage.prompt_tokens if response.usage else 0
            tokens_out = response.usage.completion_tokens if response.usage else 0

            logger.info(
                "llm_call",
                model=kwargs["model"],
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )

            # ── Persist usage if tracking context provided ──
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
                            user_id=user_id or "",
                            user_email=user_email or "",
                            model=kwargs["model"],
                            input_tokens=tokens_in,
                            output_tokens=tokens_out,
                            trigger_source=ts,
                            correlation_id=correlation_id or "",
                        )
                    finally:
                        db.close()
                except Exception as track_err:
                    logger.warning("usage_tracking_failed", error=str(track_err))

            return content
        except Exception as e:
            logger.error("llm_call_error", model=kwargs["model"], error=str(e))
            raise


# Singleton
llm_client = LLMClient()

