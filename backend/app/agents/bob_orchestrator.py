"""Bob Orchestrator — unified prompt, settings, and tool execution layer.

Shared service used by both text (bob_chat_agent.py REST) and voice
(bob_voice_pipeline.py Pipecat) transports, ensuring consistent behavior.
"""

import structlog
from typing import Optional

from app.config import settings

logger = structlog.get_logger(__name__)


class UserSettings:
    """Resolved user settings for Bob personality and voice."""

    def __init__(
        self,
        tone: str = "professional",
        formality: float = 0.5,
        response_length: str = "balanced",
        language: str = "auto",
        creativity: float = 0.3,
        emoji_usage: bool = False,
        voice: str = "",
        speed: float = 1.0,
        auto_listen: bool = True,
    ):
        self.tone = tone
        self.formality = formality
        self.response_length = response_length
        self.language = language
        self.creativity = creativity
        self.emoji_usage = emoji_usage
        self.voice = voice
        self.speed = speed
        self.auto_listen = auto_listen


def resolve_user_settings(user_id: str) -> UserSettings:
    """Load user's saved Bob settings from DB, with safe defaults."""
    try:
        from app.infrastructure.database import SessionLocal
        from app.domain.entities.bob_settings import BobUserSettings
        db = SessionLocal()
        try:
            db_settings = BobUserSettings.get_or_create(db, user_id)
            return UserSettings(
                tone=db_settings.tone or "professional",
                formality=db_settings.formality if db_settings.formality is not None else 0.5,
                response_length=db_settings.response_length or "balanced",
                language=db_settings.language or "auto",
                creativity=db_settings.creativity if db_settings.creativity is not None else 0.3,
                emoji_usage=bool(db_settings.emoji_usage),
                voice=db_settings.voice or settings.groq_tts_voice,
                speed=db_settings.speed or 1.0,
                auto_listen=db_settings.auto_listen if db_settings.auto_listen is not None else True,
            )
        finally:
            db.close()
    except Exception as e:
        logger.warning("user_settings_load_failed", user_id=user_id, error=str(e))
        return UserSettings()


def build_personality_directives(user_settings: UserSettings, for_voice: bool = False) -> str:
    """Build personality directives string from user settings."""
    tone_map = {
        "professional": "Professional and clear",
        "friendly": "Warm, friendly and approachable",
        "casual": "Casual and relaxed",
        "formal": "Formal and polished",
    }
    length_map = {
        "concise": "Keep responses very short (1 sentence when possible).",
        "balanced": "Keep responses short (1-3 sentences for voice)." if for_voice else "Keep responses concise but informative.",
        "detailed": "Give thorough responses but stay conversational.",
    }

    tone_desc = tone_map.get(user_settings.tone, "Professional and clear")
    length_desc = length_map.get(user_settings.response_length, length_map["balanced"])
    emoji_note = " You may use emoji when appropriate." if user_settings.emoji_usage else " Do NOT use emoji."

    lang = user_settings.language
    lang_label_map = {
        "en": "English",
        "fr": "French",
        "fr-FR": "French (France)",
        "fr-CA": "French (Quebec/Canada)",
        "es": "Spanish",
        "pt": "Portuguese",
    }
    lang_label = lang_label_map.get(lang, lang)

    if lang == "auto":
        language_directive = "- Language: Match the user's language. French if they speak French, English if English."
    elif lang == "fr-CA":
        language_directive = (
            "- Language: ALWAYS respond in Canadian French.\n"
            "- Prefer Canadian terms when natural: 'courriel' over 'e-mail', 'fin de semaine' over 'week-end'.\n"
            "- Use tu-form by default.\n"
            "- Keep a professional, natural tone. Do NOT force slang, joual, or heavy colloquialisms.\n"
            "- Sound like a polished Montreal professional, not a caricature."
        )
    elif lang == "fr-FR":
        language_directive = (
            "- Language: ALWAYS respond in standard French (France).\n"
            "- Use vous-form by default unless the user uses tu.\n"
            "- Keep a professional, natural tone."
        )
    else:
        language_directive = f"- Language: ALWAYS respond in {lang_label}, regardless of the user's language."

    directives = f"""
Personality settings (from user preferences):
- Tone: {tone_desc}
- {length_desc}
- Formality level: {user_settings.formality:.1f}/1.0 (higher = more formal)
- Creativity: {user_settings.creativity:.1f}/1.0 (higher = more creative/varied responses){emoji_note}
{language_directive}
"""

    return directives


def build_tts_instructions(user_settings: UserSettings) -> str:
    """Build DashScope TTS instructions for emotion and style control.

    Used with qwen3-tts-instruct-flash to produce natural, expressive speech.
    Instructions are in English (supported by DashScope instruct API).
    """
    tone_style = {
        "professional": "Speak in a clear, confident, professional manner. Moderate pace, steady intonation.",
        "friendly": "Speak warmly and cheerfully, like talking to a friend. Slightly upbeat intonation with natural enthusiasm.",
        "casual": "Speak in a relaxed, casual way with natural energy. Vary your intonation expressively, feel free to sound amused or excited.",
        "formal": "Speak with a measured, dignified pace. Clear articulation with restrained emotion. Authoritative but not cold.",
    }

    lang = user_settings.language
    accent_style = {
        "fr-CA": "Speak with a natural Quebec French accent and cadence.",
        "fr-FR": "Speak with a natural Metropolitan French (France) accent and cadence.",
        "fr": "Speak with a natural French accent.",
        "es": "Speak with a natural Spanish accent.",
        "pt": "Speak with a natural Portuguese accent.",
        "en": "Speak with a natural English accent.",
    }

    parts = [tone_style.get(user_settings.tone, tone_style["professional"])]
    if lang in accent_style:
        parts.append(accent_style[lang])

    speed = user_settings.speed
    if speed < 0.8:
        parts.append("Speak slowly and deliberately.")
    elif speed > 1.3:
        parts.append("Speak at a brisk, energetic pace.")

    return " ".join(parts)


def load_bcc_context(tenant_id: str, active_organization_id: str | None = None) -> str:
    """Load BCC profile context (vision, mission, culture, competition) for the tenant.

    Filters by tenant_id and optionally by active_organization_id to avoid
    returning profile entries from unrelated organizations.
    """
    try:
        from app.infrastructure.database import SessionLocal
        from app.domain.entities.bcc_entities import BccProfileEntry
        db = SessionLocal()
        try:
            query = (
                db.query(BccProfileEntry)
                .filter(
                    BccProfileEntry.tenant_id == tenant_id,
                    BccProfileEntry.entity_type == "organization",
                    BccProfileEntry.is_active == True,
                    BccProfileEntry.section.in_(["vision", "mission", "culture", "competition"]),
                )
            )
            if active_organization_id:
                query = query.filter(BccProfileEntry.entity_id == active_organization_id)

            entries = query.all()
            if entries:
                parts = [f"**{e.section.capitalize()}:** {e.content}" for e in entries]
                return "\n".join(parts)
        finally:
            db.close()
    except Exception as e:
        logger.warning("bcc_context_load_failed", error=str(e))
    return ""


def build_system_prompt(
    base_prompt: str,
    user_settings: UserSettings,
    bcc_context: str = "",
    mission_prompt: Optional[str] = None,
    for_voice: bool = False,
) -> str:
    """Assemble the full system prompt from all components."""
    prompt = base_prompt

    if bcc_context:
        prompt += f"\n\n# ── Organizational Context (BCC Profile) ──\n{bcc_context}\n"

    if mission_prompt:
        prompt += f"\n\n# ── Active Mission ──\n{mission_prompt}\n"

    personality = build_personality_directives(user_settings, for_voice=for_voice)
    prompt += f"\n\n{personality}"

    return prompt


def get_llm_temperature(user_settings: UserSettings) -> float:
    """Map creativity (0-1) to LLM temperature."""
    return max(0.1, min(1.0, user_settings.creativity))


async def execute_tool(tool_name: str, args: dict, user_context: dict) -> dict:
    """Execute a Bob tool through the centralized tool executor."""
    from app.agents.tool_executor import execute_bob_tool
    from app.infrastructure.database import SessionLocal

    db = SessionLocal()
    try:
        return await execute_bob_tool(tool_name, args, user_context, db)
    finally:
        db.close()
