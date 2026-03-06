"""Groq LLM client — reusable wrapper.

UNRULED PATTERN — No HDQ template exists for LLM client integration.
"""

from typing import Optional

from groq import Groq
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class LLMClient:
    """Client for Groq API — chat completions with JSON mode support."""

    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.default_model = settings.groq_default_model

    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat completion request to Groq.

        Args:
            prompt: User message
            system_prompt: System message (optional)
            model: Model override (defaults to settings)
            json_mode: Enable JSON response format
            temperature: Creativity (0.0-1.0)
            max_tokens: Max response tokens

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
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            logger.info(
                "llm_call",
                model=kwargs["model"],
                tokens_in=response.usage.prompt_tokens if response.usage else 0,
                tokens_out=response.usage.completion_tokens if response.usage else 0,
            )
            return content
        except Exception as e:
            logger.error("llm_call_error", model=kwargs["model"], error=str(e))
            raise


# Singleton
llm_client = LLMClient()
