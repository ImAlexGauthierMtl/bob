"""Cost tracker — structured logging for Groq API usage.

Logs every STT/LLM/TTS call with tokens, duration, and estimated
cost for analytics. Uses structlog for consistent log format.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# Groq pricing (as of 2026-03)
GROQ_PRICING = {
    "qwen3-32b": {"input": 0.29 / 1_000_000, "output": 0.59 / 1_000_000},
    "llama-3.3-70b-versatile": {"input": 0.59 / 1_000_000, "output": 0.79 / 1_000_000},
    "whisper-large-v3-turbo": {"per_second": 0.04 / 3600},  # $0.04/hour
    "playai-tts": {"per_char": 0.015 / 1000},  # $15/M chars
}


@dataclass
class UsageRecord:
    """Single API call usage record."""

    service: str  # "stt", "llm", "tts"
    model: str
    user_id: str
    session_id: str
    duration_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    audio_seconds: float = 0.0
    characters: int = 0
    estimated_cost_usd: float = 0.0
    timestamp: float = field(default_factory=time.time)


class CostTracker:
    """Tracks and logs API usage for cost monitoring."""

    def __init__(self):
        self._records: list[UsageRecord] = []

    def log_llm_call(
        self,
        model: str,
        user_id: str,
        session_id: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: float,
    ) -> UsageRecord:
        """Log an LLM API call."""
        pricing = GROQ_PRICING.get(model, {"input": 0, "output": 0})
        cost = (input_tokens * pricing.get("input", 0)) + (
            output_tokens * pricing.get("output", 0)
        )

        record = UsageRecord(
            service="llm",
            model=model,
            user_id=user_id,
            session_id=session_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=duration_ms,
            estimated_cost_usd=cost,
        )
        self._records.append(record)

        logger.info(
            "api_usage_llm",
            model=model,
            user_id=user_id,
            session_id=session_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_ms=round(duration_ms, 1),
            cost_usd=round(cost, 6),
        )

        return record

    def log_stt_call(
        self,
        model: str,
        user_id: str,
        session_id: str,
        audio_seconds: float,
        duration_ms: float,
    ) -> UsageRecord:
        """Log an STT API call."""
        pricing = GROQ_PRICING.get(model, {"per_second": 0})
        cost = audio_seconds * pricing.get("per_second", 0)

        record = UsageRecord(
            service="stt",
            model=model,
            user_id=user_id,
            session_id=session_id,
            audio_seconds=audio_seconds,
            duration_ms=duration_ms,
            estimated_cost_usd=cost,
        )
        self._records.append(record)

        logger.info(
            "api_usage_stt",
            model=model,
            user_id=user_id,
            session_id=session_id,
            audio_seconds=round(audio_seconds, 1),
            duration_ms=round(duration_ms, 1),
            cost_usd=round(cost, 6),
        )

        return record

    def log_tts_call(
        self,
        model: str,
        user_id: str,
        session_id: str,
        characters: int,
        duration_ms: float,
    ) -> UsageRecord:
        """Log a TTS API call."""
        pricing = GROQ_PRICING.get(model, {"per_char": 0})
        cost = characters * pricing.get("per_char", 0)

        record = UsageRecord(
            service="tts",
            model=model,
            user_id=user_id,
            session_id=session_id,
            characters=characters,
            duration_ms=duration_ms,
            estimated_cost_usd=cost,
        )
        self._records.append(record)

        logger.info(
            "api_usage_tts",
            model=model,
            user_id=user_id,
            session_id=session_id,
            characters=characters,
            duration_ms=round(duration_ms, 1),
            cost_usd=round(cost, 6),
        )

        return record

    def get_user_total(self, user_id: str) -> dict:
        """Get total usage stats for a user."""
        user_records = [r for r in self._records if r.user_id == user_id]
        total_cost = sum(r.estimated_cost_usd for r in user_records)
        return {
            "user_id": user_id,
            "total_calls": len(user_records),
            "total_estimated_cost_usd": round(total_cost, 4),
            "breakdown": {
                "llm": len([r for r in user_records if r.service == "llm"]),
                "stt": len([r for r in user_records if r.service == "stt"]),
                "tts": len([r for r in user_records if r.service == "tts"]),
            },
        }

    def get_session_total(self, session_id: str) -> dict:
        """Get total usage stats for a session."""
        records = [r for r in self._records if r.session_id == session_id]
        total_cost = sum(r.estimated_cost_usd for r in records)
        return {
            "session_id": session_id,
            "total_calls": len(records),
            "total_estimated_cost_usd": round(total_cost, 4),
        }


# Singleton
cost_tracker = CostTracker()
