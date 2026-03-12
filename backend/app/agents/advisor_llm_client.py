"""Advisor LLM Client — Kimi K2.5 via OpenRouter for business advisory.

Provides the core LLM interface for the Business Advisor mode.
Integrates:
  - Kimi K2.5 (128k context) via OpenRouter
  - Serper web search for market data
  - BCC organizational context injection
  - Usage tracking per call

The advisor maintains conversation history for multi-turn sessions.
"""

import json
import structlog
import httpx
from typing import Optional

from app.config import settings
from app.infrastructure.provider_resilience import retry_with_backoff

logger = structlog.get_logger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
SERPER_SEARCH_URL = "https://google.serper.dev/search"

ADVISOR_SYSTEM_PROMPT = """\
You are **Bob**, a senior business advisor and strategic consultant.

## Your Role
You provide executive-level business analysis, strategic recommendations, and operational insights.
You think deeply, consider multiple angles, and deliver structured, actionable advice.

## Your Knowledge Base
You have access to the organization's internal knowledge (vision, mission, culture, regulations, industries).
This context is provided below. Use it to ground your advice in the company's reality.

## Communication Style
- Be direct and structured — use headers, bullet points, and bold for key insights
- Start with the strategic overview, then drill into specifics
- Quantify when possible — numbers, percentages, timelines
- End with clear, actionable next steps
- Respond in the same language as the user

## Guardrails
- NEVER provide specific legal, tax, or medical advice — suggest consulting a professional
- You MAY discuss regulatory implications, compliance strategy, and risk management
- You MAY discuss financial strategy, budgeting, and investment analysis
- Always disclose when information comes from web search vs. your training data
- If web search results are provided, cite them naturally in your response

## Web Search Results
When web search data is included, integrate it naturally into your analysis.
Format citations as: *(Source: [title])*

{org_context}
"""


def _search_web(query: str, num_results: int = 5) -> list[dict]:
    """Search the web via Serper for market data and current information.

    Args:
        query: Search query string.
        num_results: Number of results to return.

    Returns:
        List of search results with title, link, snippet.
    """
    if not settings.serper_api_key:
        logger.warning("serper_key_missing", action="skip_web_search")
        return []

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                SERPER_SEARCH_URL,
                json={"q": query, "num": num_results},
                headers={
                    "X-API-KEY": settings.serper_api_key,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("organic", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })

        # Track search usage
        try:
            from app.infrastructure.database import SessionLocal
            from app.middleware.usage_tracker import UsageTracker
            from app.domain.entities.usage_transaction import TriggerSource

            db = SessionLocal()
            try:
                tracker = UsageTracker(db)
                tracker.track_search(
                    tenant_id="",
                    user_id="",
                    user_email="",
                    provider="serper",
                    trigger_source=TriggerSource.BOB_CHAT,
                    metadata={"query": query, "results": len(results), "source": "advisor"},
                )
                db.commit()
            finally:
                db.close()
        except Exception as track_err:
            logger.warning("advisor_search_track_error", error=str(track_err))

        logger.info("advisor_web_search", query=query, results=len(results))
        return results

    except Exception as e:
        logger.error("advisor_web_search_error", query=query, error=str(e))
        return []


def _needs_web_search(message: str) -> Optional[str]:
    """Determine if a message needs web search and generate a search query.

    Simple heuristic — checks for market/trend/competitor/data keywords.
    Returns a search query or None.
    """
    search_indicators = [
        "marché", "market", "tendance", "trend", "concurrent", "competitor",
        "industrie", "industry", "données", "data", "statistique", "stats",
        "benchmark", "prix", "price", "croissance", "growth", "revenue",
        "actualité", "news", "récent", "recent", "2025", "2026",
        "comparaison", "comparison", "analyse", "analysis",
    ]

    message_lower = message.lower()
    needs_search = any(kw in message_lower for kw in search_indicators)

    if not needs_search:
        return None

    # Use the message itself as the search query (trimmed)
    query = message[:200].strip()
    return query


@retry_with_backoff(max_retries=2, base_delay=3.0, max_delay=15.0)
def advisor_chat(
    message: str,
    conversation_history: list[dict],
    org_context: str = "",
    tenant_id: str = "",
    user_id: str = "",
    user_email: str = "",
) -> str:
    """Send a message to the Business Advisor (Kimi K2.5 via OpenRouter).

    Args:
        message: User's current message.
        conversation_history: Previous messages [{"role": "user"/"assistant", "content": "..."}].
        org_context: BCC organizational context (pre-loaded).
        tenant_id: For usage tracking.
        user_id: For usage tracking.
        user_email: For usage tracking.

    Returns:
        Advisor response text.
    """
    api_key = settings.openrouter_api_key
    if not api_key:
        return "⚠️ OpenRouter API key not configured. Please set OPENROUTER_API_KEY in your environment."

    model = settings.kb_generation_model  # moonshotai/kimi-k2.5

    # Check if we need web search
    search_query = _needs_web_search(message)
    web_context = ""
    if search_query:
        results = _search_web(search_query)
        if results:
            web_lines = ["\n## Web Search Results\n"]
            for r in results:
                web_lines.append(f"**{r['title']}**\n{r['snippet']}\n*({r['link']})*\n")
            web_context = "\n".join(web_lines)

    # Build system prompt with org context and web data
    system = ADVISOR_SYSTEM_PROMPT.replace("{org_context}", org_context)
    if web_context:
        system += f"\n\n{web_context}"

    # Build messages array
    messages = [{"role": "system", "content": system}]

    # Add conversation history (last 20 messages to fit in context)
    for msg in conversation_history[-20:]:
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", ""),
        })

    # Add current message
    messages.append({"role": "user", "content": message})

    # Call Kimi K2.5
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 8192,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://croo.digital",
        "X-Title": "Bob Business Advisor",
    }

    logger.info(
        "advisor_llm_request",
        model=model,
        message_count=len(messages),
        has_web_search=bool(web_context),
        has_org_context=bool(org_context),
    )

    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            OPENROUTER_API_URL,
            json=payload,
            headers=headers,
        )

    if response.status_code != 200:
        error_text = response.text[:500]
        logger.error("advisor_llm_error", status=response.status_code, error=error_text)
        return "⚠️ I encountered an error processing your request. Please try again."

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        return "⚠️ No response generated. Please try rephrasing your question."

    content = choices[0].get("message", {}).get("content", "")

    usage = data.get("usage", {})
    tokens_in = usage.get("prompt_tokens", 0)
    tokens_out = usage.get("completion_tokens", 0)

    logger.info(
        "advisor_llm_response",
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        content_length=len(content),
    )

    # Track usage
    if tenant_id:
        try:
            from app.infrastructure.database import SessionLocal
            from app.middleware.usage_tracker import UsageTracker
            from app.domain.entities.usage_transaction import TriggerSource

            db = SessionLocal()
            try:
                tracker = UsageTracker(db)
                tracker.track_llm(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    user_email=user_email,
                    provider="openrouter",
                    model=model,
                    input_tokens=tokens_in,
                    output_tokens=tokens_out,
                    trigger_source=TriggerSource.BOB_CHAT,
                    correlation_id="advisor",
                )
                db.commit()
            finally:
                db.close()
        except Exception as track_err:
            logger.warning("advisor_usage_track_error", error=str(track_err))

    return content
