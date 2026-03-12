"""KB LLM Client — OpenRouter integration for KB article content generation.

Uses Kimi K2.5 via OpenRouter to generate rich, structured KB article content.
Separated from the main Groq LLM client to allow using a different model
optimized for long-form content generation.
"""

import json
import structlog
import httpx
from typing import Optional

from app.config import settings

logger = structlog.get_logger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


async def generate_kb_content(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    """Generate KB article content using Kimi K2.5 via OpenRouter.

    Args:
        system_prompt: System instructions for tone, style, and structure.
        user_prompt: The specific article generation prompt.
        model: Override model (defaults to config kb_generation_model).
        temperature: Creativity level (0.7 for balanced content).
        max_tokens: Max response length (8K for long articles).

    Returns:
        Generated markdown content string.

    Raises:
        RuntimeError: If API call fails or returns no content.
    """
    api_key = settings.openrouter_api_key
    if not api_key:
        raise RuntimeError(
            "OpenRouter API key not configured. Set OPENROUTER_API_KEY in .env"
        )

    target_model = model or settings.kb_generation_model

    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://croo.digital",
        "X-Title": "Bob KB Generator",
    }

    logger.info(
        "kb_llm_request",
        model=target_model,
        prompt_length=len(user_prompt),
        max_tokens=max_tokens,
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            OPENROUTER_API_URL,
            json=payload,
            headers=headers,
        )

        if response.status_code != 200:
            error_text = response.text[:500]
            logger.error(
                "kb_llm_error",
                status=response.status_code,
                error=error_text,
            )
            raise RuntimeError(
                f"OpenRouter API error ({response.status_code}): {error_text}"
            )

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenRouter returned no choices")

        content = choices[0].get("message", {}).get("content", "")
        if not content:
            raise RuntimeError("OpenRouter returned empty content")

        usage = data.get("usage", {})
        logger.info(
            "kb_llm_response",
            model=target_model,
            content_length=len(content),
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
        )

        return content


def generate_kb_content_sync(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    """Synchronous wrapper for generate_kb_content.

    Used by the workflow engine which runs in a sync context.
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already in an async context — run in a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(
                asyncio.run,
                generate_kb_content(
                    system_prompt, user_prompt, model, temperature, max_tokens
                ),
            )
            return future.result(timeout=130)
    else:
        return asyncio.run(
            generate_kb_content(
                system_prompt, user_prompt, model, temperature, max_tokens
            )
        )
