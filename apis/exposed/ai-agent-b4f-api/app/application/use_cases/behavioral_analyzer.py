"""Behavioral Analyzer — AI-driven psychological profiling from CRM interactions.

B4F version: fetches client map data via HTTP client, runs LLM analysis,
then updates client map via HTTP client.
"""

import json
import structlog

logger = structlog.get_logger(__name__)


class BehavioralAnalyzer:
    """Analyze interaction patterns to build a behavioral profile."""

    def __init__(self, client_map_client):
        self.client_map_client = client_map_client

    async def analyze(
        self,
        contact_id: str,
        tenant_id: str,
        forward_headers: dict = None,
    ) -> dict:
        """Run behavioral analysis pipeline via HTTP client + LLM."""
        # Fetch client map from backend
        client_map = await self.client_map_client.get(contact_id, forward_headers=forward_headers)
        if not client_map:
            client_map = await self.client_map_client.upsert(contact_id, {}, forward_headers=forward_headers)

        # Build signals from the client map data
        signals = self._build_signals_from_map(client_map)

        # LLM analysis
        profile = await self._llm_analyze(signals)

        # Update client map with behavioral profile via backend
        await self.client_map_client.upsert(
            contact_id,
            {"behavioral_profile": profile},
            forward_headers=forward_headers,
        )

        logger.info(
            "behavioral_analysis_complete",
            contact_id=contact_id,
            disc_primary=profile.get("disc_primary"),
        )
        return profile

    def _build_signals_from_map(self, client_map: dict) -> dict:
        """Extract behavioral signals from client map data."""
        signals = {
            "golden_note_signals": {},
            "client_map_context": {},
        }

        golden_notes = client_map.get("golden_notes", [])
        if golden_notes:
            emotional_sequence = [n.get("emotional_climate", "NEUTRAL") for n in golden_notes]
            interaction_types = [n.get("interaction_type", "UNKNOWN") for n in golden_notes]
            verbatims = [n.get("verbatim") for n in golden_notes if n.get("verbatim")]

            signals["golden_note_signals"] = {
                "total_notes": len(golden_notes),
                "emotional_sequence": emotional_sequence[:10],
                "interaction_type_distribution": interaction_types[:10],
                "sample_verbatims": verbatims[:3],
            }

        signals["client_map_context"] = {
            "role_type": client_map.get("role_type"),
            "disc_profile": client_map.get("disc_profile"),
            "company_culture": client_map.get("company_culture"),
            "pain_point": client_map.get("pain_point"),
            "ego_driver": client_map.get("ego_driver"),
            "trust_level": client_map.get("trust_level"),
            "meddpicc_score": client_map.get("meddpicc_score"),
        }

        return signals

    async def _llm_analyze(self, signals: dict) -> dict:
        """Call LLM to infer behavioral profile from signals."""
        try:
            from groq import Groq
            from shared.config import get_settings
            settings = get_settings("ai-agent")

            prompt = f"""Analyze these CRM interaction signals and produce a behavioral profile.

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
  "persuasion_keys": ["data_driven_arguments", ...],
  "communication_tips": ["tip 1", "tip 2", "tip 3"]
}}"""

            client = Groq(api_key=settings.groq_api_key)
            response = client.chat.completions.create(
                model=settings.workspace_model,
                messages=[
                    {"role": "system", "content": "You are a behavioral analysis AI. Respond only with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1024,
            )

            raw = response.choices[0].message.content or "{}"
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1]
            if raw.endswith("```"):
                raw = raw.rsplit("```", 1)[0]
            raw = raw.strip()

            profile = json.loads(raw)
            logger.info("behavioral_llm_done", disc=profile.get("disc_primary"))
            return profile

        except Exception as e:
            logger.error("behavioral_llm_failed", error=str(e))
            return {
                "disc_primary": "UNKNOWN",
                "disc_confidence": 0.0,
                "disc_reasoning": f"Analysis failed: {str(e)[:100]}",
                "decision_speed": "unknown",
                "formality_level": "neutral",
                "risk_tolerance": "moderate",
                "preferred_channel": "mixed",
                "emotional_baseline": "insufficient data",
                "emotional_trend": "stable",
                "communication_tips": ["Insufficient interaction data for accurate analysis"],
            }
