"""LLM-backed behavioral profile provider for the internal Agent Backend."""

import json
import os
from typing import Any

from shared.infrastructure import get_logger

logger = get_logger(__name__)


def fallback_behavioral_profile(reason: str = "insufficient data") -> dict[str, Any]:
    return {
        "disc_primary": "UNKNOWN",
        "disc_confidence": 0.0,
        "disc_reasoning": reason,
        "decision_speed": "unknown",
        "formality_level": "neutral",
        "risk_tolerance": "moderate",
        "preferred_channel": "mixed",
        "emotional_baseline": "insufficient data",
        "emotional_trend": "stable",
        "communication_tips": ["Insufficient interaction data for accurate analysis"],
    }


class GroqBehavioralProfileProvider:
    async def analyze(self, signals: dict[str, Any]) -> dict[str, Any]:
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key:
            return fallback_behavioral_profile("GROQ_API_KEY not configured")

        try:
            from groq import Groq

            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model=os.environ.get("WORKSPACE_MODEL", "llama-3.1-8b-instant"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are a behavioral analysis AI. Respond only with valid JSON.",
                    },
                    {"role": "user", "content": self._prompt(signals)},
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            raw = (response.choices[0].message.content or "{}").strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw.rsplit("```", 1)[0]
            return json.loads(raw.strip())
        except Exception as exc:
            logger.error("behavioral_profile_provider_failed", error=str(exc))
            return fallback_behavioral_profile(f"Analysis failed: {str(exc)[:100]}")

    def _prompt(self, signals: dict[str, Any]) -> str:
        return f"""Analyze these CRM interaction signals and produce a behavioral profile.

SIGNALS:
{json.dumps(signals, indent=2, ensure_ascii=False, default=str)}

Respond ONLY with a valid JSON object (no markdown, no explanation) with these fields:
{{
  "disc_primary": "D|I|S|C",
  "disc_secondary": "D|I|S|C|null",
  "disc_confidence": 0.0-1.0,
  "disc_reasoning": "brief explanation",
  "decision_speed": "fast_decisive|moderate|slow_analytical",
  "formality_level": "informal|neutral|formal",
  "risk_tolerance": "risk_taker|moderate|conservative",
  "preferred_channel": "email|call|meeting|mixed",
  "emotional_baseline": "description",
  "emotional_trend": "improving|stable|declining",
  "engagement_momentum": "description",
  "persuasion_keys": ["data_driven_arguments"],
  "communication_tips": ["tip 1", "tip 2", "tip 3"]
}}"""
