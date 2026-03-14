"""Behavioral Analyzer — AI-driven psychological profiling from CRM interactions.

Pipeline:
  1. SQL Aggregator — compute behavioral signals from emails, events, activities, golden notes
  2. LLM Profiler  — single Kimi K2 call to generate structured DISC + behavioral profile
"""

import json
import structlog
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.domain.entities.client_map import ClientMap, GoldenNote

logger = structlog.get_logger(__name__)


class BehavioralAnalyzer:
    """Analyze interaction patterns to build a behavioral profile."""

    def __init__(self, db: Session):
        self.db = db

    async def analyze(
        self,
        contact_id: str,
        tenant_id: str,
        client_map: ClientMap,
    ) -> dict:
        """Run full behavioral analysis pipeline.

        Returns:
            dict: Behavioral profile JSON stored on client_map.behavioral_profile
        """
        # Step 1: Aggregate signals
        signals = self._aggregate_signals(contact_id, tenant_id, client_map)

        # Step 2: LLM analysis
        profile = await self._llm_analyze(signals)

        # Step 3: Persist
        client_map.behavioral_profile = profile
        client_map.last_behavioral_analysis = datetime.utcnow()
        self.db.commit()

        logger.info(
            "behavioral_analysis_complete",
            contact_id=contact_id,
            disc_primary=profile.get("disc_primary"),
        )
        return profile

    def _aggregate_signals(
        self,
        contact_id: str,
        tenant_id: str,
        client_map: ClientMap,
    ) -> dict:
        """Compute behavioral signals from existing CRM data."""
        signals: dict = {
            "email_signals": {},
            "event_signals": {},
            "golden_note_signals": {},
            "activity_signals": {},
        }

        # ── Email signals ────────────────────────────────────
        try:
            from app.domain.entities.synced_email import SyncedEmail

            emails = (
                self.db.query(SyncedEmail)
                .filter(
                    SyncedEmail.linked_contact_id == contact_id,
                )
                .order_by(desc(SyncedEmail.received_at))
                .limit(50)
                .all()
            )

            if emails:
                # Response times (from their replies)
                email_lengths = []
                send_hours = []
                send_days = []

                for e in emails:
                    if e.body_preview:
                        email_lengths.append(len(e.body_preview.split()))
                    if e.received_at:
                        send_hours.append(e.received_at.hour)
                        send_days.append(e.received_at.strftime("%A").lower())

                signals["email_signals"] = {
                    "total_emails": len(emails),
                    "avg_email_length_words": round(sum(email_lengths) / len(email_lengths)) if email_lengths else 0,
                    "preferred_hours": list(set(sorted(send_hours[:10]))),
                    "preferred_days": list(set(send_days[:10])),
                    "importance_high_count": sum(1 for e in emails if e.importance == "high"),
                }
        except Exception as e:
            logger.warning("email_signal_error", error=str(e))

        # ── Calendar event signals ───────────────────────────
        try:
            from app.domain.entities.synced_event import SyncedEvent

            events = (
                self.db.query(SyncedEvent)
                .filter(
                    SyncedEvent.linked_contact_id == contact_id,
                )
                .order_by(desc(SyncedEvent.start_time))
                .limit(30)
                .all()
            )

            if events:
                durations = []
                for ev in events:
                    if ev.start_time and ev.end_time:
                        dur = (ev.end_time - ev.start_time).total_seconds() / 60
                        durations.append(dur)

                signals["event_signals"] = {
                    "total_meetings": len(events),
                    "avg_meeting_duration_min": round(sum(durations) / len(durations)) if durations else 0,
                    "cancelled_count": sum(1 for ev in events if ev.is_cancelled),
                }
        except Exception as e:
            logger.warning("event_signal_error", error=str(e))

        # ── Golden Note signals ──────────────────────────────
        try:
            notes = (
                self.db.query(GoldenNote)
                .filter(
                    GoldenNote.client_map_id == client_map.id,
                    GoldenNote.is_deleted == False,
                )
                .order_by(desc(GoldenNote.interaction_date))
                .limit(10)
                .all()
            )

            if notes:
                emotional_sequence = [
                    n.emotional_climate.value if n.emotional_climate else "NEUTRAL"
                    for n in notes
                ]
                interaction_types = [
                    n.interaction_type.value if n.interaction_type else "UNKNOWN"
                    for n in notes
                ]
                verbatims = [n.verbatim for n in notes if n.verbatim]

                signals["golden_note_signals"] = {
                    "total_notes": len(notes),
                    "emotional_sequence": emotional_sequence,
                    "interaction_type_distribution": interaction_types,
                    "sample_verbatims": verbatims[:3],
                    "silences_observed": sum(1 for n in notes if n.silence_observed),
                }
        except Exception as e:
            logger.warning("golden_note_signal_error", error=str(e))

        # ── Activity signals ─────────────────────────────────
        try:
            from app.domain.entities.activity import Activity, activity_contacts

            activities = (
                self.db.query(Activity)
                .join(activity_contacts, Activity.id == activity_contacts.c.activity_id)
                .filter(
                    activity_contacts.c.contact_id == contact_id,
                    Activity.tenant_id == tenant_id,
                )
                .order_by(desc(Activity.created_at))
                .limit(20)
                .all()
            )

            if activities:
                type_counts: dict = {}
                for a in activities:
                    at = str(a.activity_type) if a.activity_type else "UNKNOWN"
                    type_counts[at] = type_counts.get(at, 0) + 1

                signals["activity_signals"] = {
                    "total_activities": len(activities),
                    "type_distribution": type_counts,
                }
        except Exception as e:
            logger.warning("activity_signal_error", error=str(e))

        return signals

    async def _llm_analyze(self, signals: dict) -> dict:
        """Call Kimi K2 to infer behavioral profile from signals."""
        from groq import Groq
        from app.config import settings

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
  "preferred_schedule": {{"days": ["monday",...], "time": "morning|afternoon|evening"}},
  "emotional_baseline": "description",
  "emotional_trend": "improving|stable|declining",
  "engagement_momentum": "description with % if possible",
  "persuasion_keys": ["data_driven_arguments", ...],
  "communication_tips": ["tip 1", "tip 2", "tip 3"]
}}"""

        try:
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
            # Strip markdown code fences if present
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
            # Return a minimal default profile
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
