"""Bob settings routes — user-level Bob personality and voice configuration.

Stores per-user Bob settings in the database (BobUserSettings table).
Settings persist across server restarts.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.presentation.routes.auth_routes import get_current_user
from app.infrastructure.database import SessionLocal
from app.domain.entities.bob_settings import BobUserSettings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/bob/settings")


# ── Schemas ──────────────────────────────────────

class BobPersonality(BaseModel):
    """Bob's personality configuration."""
    tone: str = Field(default="professional", description="Tone: professional, friendly, casual, formal")
    formality: float = Field(default=0.5, ge=0.0, le=1.0, description="Formality level 0-1")
    response_length: str = Field(default="balanced", description="Length: concise, balanced, detailed")
    language: str = Field(default="auto", description="Response language: auto, en, fr, es, pt")
    creativity: float = Field(default=0.3, ge=0.0, le=1.0, description="Creativity/temperature 0-1")
    emoji_usage: bool = Field(default=False, description="Allow emoji in responses")


class BobVoiceSettings(BaseModel):
    """Bob's voice configuration for TTS."""
    voice: str = Field(default="autumn", description="Orpheus TTS voice name")
    speed: float = Field(default=1.0, ge=0.5, le=3.0, description="Speech speed 0.5-3.0")
    auto_listen: bool = Field(default=True, description="Auto-activate listening after Bob speaks")


class BobSettingsRequest(BaseModel):
    """Full Bob settings payload."""
    personality: BobPersonality = Field(default_factory=BobPersonality)
    voice: BobVoiceSettings = Field(default_factory=BobVoiceSettings)


class BobSettingsResponse(BaseModel):
    """Bob settings response with available options."""
    personality: BobPersonality
    voice: BobVoiceSettings
    available_voices: list[dict]
    available_tones: list[str]
    available_languages: list[dict]


# ── Available options ────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Qwen3-TTS-Flash voice catalog — from official Alibaba Cloud documentation.
# All voices support: Chinese, English, French, German, Russian, Italian,
# Spanish, Portuguese, Japanese, Korean.
# Accent labels (FR-CA / FR-France / International) are curated by phoneme
# quality and subjective tests; no official dialect-specific voices exist.
# ─────────────────────────────────────────────────────────────────────────────

# Voix féminine — caractère chaleureux / accessible (idéales fr-CA)
_QWEN_FEMALE_WARM = [
    {"id": "Cherry",   "name": "Cherry",   "gender": "female", "style": "Chaleureuse & Naturelle"},
    {"id": "Serena",   "name": "Serena",   "gender": "female", "style": "Douce & Intentionnelle"},
    {"id": "Maia",     "name": "Maia",     "gender": "female", "style": "Intelligente & Douce"},
    {"id": "Mia",      "name": "Mia",      "gender": "female", "style": "Apaisante & Délicate"},
    {"id": "Vivian",   "name": "Vivian",   "gender": "female", "style": "Confiante & Espiègle"},
    {"id": "Momo",     "name": "Momo",     "gender": "female", "style": "Enjouée & Pétillante"},
]

# Voix féminine — caractère pro / élégant (idéales fr-France)
_QWEN_FEMALE_PRO = [
    {"id": "Jennifer", "name": "Jennifer", "gender": "female", "style": "Cinématique & Premium"},
    {"id": "Katerina", "name": "Katerina", "gender": "female", "style": "Posée & Mémorable"},
    {"id": "Elias",    "name": "Elias",    "gender": "female", "style": "Académique & Précise"},
    {"id": "Bellona",  "name": "Bellona",  "gender": "female", "style": "Puissante & Théâtrale"},
    {"id": "Bella",    "name": "Bella",    "gender": "female", "style": "Légère & Pétillante"},
]

# Voix masculine — caractère dynamique / accessible (idéales fr-CA)
_QWEN_MALE_WARM = [
    {"id": "Ethan",    "name": "Ethan",    "gender": "male", "style": "Solaire & Énergique"},
    {"id": "Aiden",    "name": "Aiden",    "gender": "male", "style": "Décontracté & Accessible"},
    {"id": "Mochi",    "name": "Mochi",    "gender": "male", "style": "Vif & Espiègle"},
    {"id": "Kai",      "name": "Kai",      "gender": "male", "style": "Apaisant & Enveloppant"},
    {"id": "Moon",     "name": "Moon",     "gender": "male", "style": "Audacieux & Charismatique"},
]

# Voix masculine — caractère formel / expressif (idéales fr-France)
_QWEN_MALE_PRO = [
    {"id": "Ryan",     "name": "Ryan",     "gender": "male", "style": "Dramatique & Expressif"},
    {"id": "Neil",     "name": "Neil",     "gender": "male", "style": "Articulé & Journalistique"},
    {"id": "Vincent",  "name": "Vincent",  "gender": "male", "style": "Rauque & Cinématique"},
    {"id": "Arthur",   "name": "Arthur",   "gender": "male", "style": "Rustique & Chaleureux"},
    {"id": "Eldric Sage", "name": "Eldric Sage", "gender": "male", "style": "Sage & Posé"},
]

# Voix custom clonée
_QWEN_CUSTOM = [
    {"id": "Rick", "name": "Rick ⭐", "gender": "male", "style": "Voix clonée — Ricardo"},
]


def _build_voice_list(voices: list[dict], accent: str, provider: str = "qwen") -> list[dict]:
    return [{**v, "accent": accent, "provider": provider} for v in voices]


QWEN_VOICES_FR_CA = (
    _build_voice_list(_QWEN_CUSTOM, "Custom")
    + _build_voice_list(_QWEN_FEMALE_WARM, "FR Québec")
    + _build_voice_list(_QWEN_MALE_WARM, "FR Québec")
    + _build_voice_list(_QWEN_FEMALE_PRO, "FR Québec")
    + _build_voice_list(_QWEN_MALE_PRO, "FR Québec")
)

QWEN_VOICES_FR_FR = (
    _build_voice_list(_QWEN_CUSTOM, "Custom")
    + _build_voice_list(_QWEN_FEMALE_PRO, "FR France")
    + _build_voice_list(_QWEN_MALE_PRO, "FR France")
    + _build_voice_list(_QWEN_FEMALE_WARM, "FR France")
    + _build_voice_list(_QWEN_MALE_WARM, "FR France")
)

QWEN_VOICES_INTL = (
    _build_voice_list(_QWEN_CUSTOM, "Custom")
    + _build_voice_list(_QWEN_FEMALE_WARM + _QWEN_FEMALE_PRO, "International")
    + _build_voice_list(_QWEN_MALE_WARM + _QWEN_MALE_PRO, "International")
)


# Groq Orpheus voices — English only
ORPHEUS_VOICES = [
    {"id": "autumn", "name": "Autumn", "gender": "female", "accent": "American", "style": "Warm & Natural",          "provider": "orpheus"},
    {"id": "diana",  "name": "Diana",  "gender": "female", "accent": "American", "style": "Clear & Professional",   "provider": "orpheus"},
    {"id": "hannah", "name": "Hannah", "gender": "female", "accent": "American", "style": "Friendly & Expressive",  "provider": "orpheus"},
    {"id": "austin", "name": "Austin", "gender": "male",   "accent": "American", "style": "Confident & Engaging",   "provider": "orpheus"},
    {"id": "daniel", "name": "Daniel", "gender": "male",   "accent": "American", "style": "Deep & Authoritative",   "provider": "orpheus"},
    {"id": "troy",   "name": "Troy",   "gender": "male",   "accent": "American", "style": "Energetic & Dynamic",    "provider": "orpheus"},
]

# Languages that use Qwen3-TTS (multilingual voices).
# "auto" is intentionally excluded — defaults to Orpheus in the pipeline.
QWEN_LANGUAGE_CODES = {"fr", "fr-FR", "fr-CA", "es", "pt"}

AVAILABLE_TONES = ["professional", "friendly", "casual", "formal"]


AVAILABLE_LANGUAGES = [
    {"code": "auto", "name": "Auto-detect"},
    {"code": "en",   "name": "English"},
    {"code": "fr-CA", "name": "Français (Canada / Québec)"},
    {"code": "fr-FR", "name": "Français (France)"},
    {"code": "es",   "name": "Español"},
    {"code": "pt",   "name": "Português"},
]


def _voices_for_language(language: str) -> list[dict]:
    """Return the appropriate voice list based on the selected language.

    - "en"   → Orpheus voices (English-only, expressive)
    - "fr-CA" → Qwen FR-CA voices
    - "fr-FR" → Qwen FR-FR voices
    - "fr"   → Qwen international (neutral FR)
    - "es","pt" → Qwen international
    - "auto"  → Orpheus voices (pipeline default for auto is Orpheus)
    """
    if language == "fr-CA":
        return QWEN_VOICES_FR_CA
    if language == "fr-FR":
        return QWEN_VOICES_FR_FR
    if language in QWEN_LANGUAGE_CODES:
        return QWEN_VOICES_INTL
    # "en" and "auto" → Orpheus
    return ORPHEUS_VOICES


def _db_to_response(s: BobUserSettings) -> BobSettingsResponse:
    """Convert a DB row to the API response model."""
    voices = _voices_for_language(s.language)
    return BobSettingsResponse(
        personality=BobPersonality(
            tone=s.tone,
            formality=s.formality,
            response_length=s.response_length,
            language=s.language,
            creativity=s.creativity,
            emoji_usage=s.emoji_usage,
        ),
        voice=BobVoiceSettings(
            voice=s.voice,
            speed=s.speed,
            auto_listen=s.auto_listen,
        ),
        available_voices=voices,
        available_tones=AVAILABLE_TONES,
        available_languages=AVAILABLE_LANGUAGES,
    )


# ── Routes ───────────────────────────────────────

@router.get("", response_model=BobSettingsResponse)
async def get_bob_settings(
    current_user: dict = Depends(get_current_user),
):
    """Get current Bob settings for the authenticated user."""
    user_id = current_user["user_id"]
    db = SessionLocal()
    try:
        settings = BobUserSettings.get_or_create(db, user_id)
        return _db_to_response(settings)
    finally:
        db.close()


@router.put("", response_model=BobSettingsResponse)
async def update_bob_settings(
    request: BobSettingsRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update Bob settings for the authenticated user."""
    user_id = current_user["user_id"]

    # Validate voice exists in the appropriate provider list
    all_qwen_voice_ids = {v["id"] for v in QWEN_VOICES_FR_CA + QWEN_VOICES_FR_FR + QWEN_VOICES_INTL}
    all_voice_ids = {v["id"] for v in ORPHEUS_VOICES} | all_qwen_voice_ids

    if request.voice.voice not in all_voice_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid voice: {request.voice.voice}",
        )

    # Validate tone
    if request.personality.tone not in AVAILABLE_TONES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tone: {request.personality.tone}",
        )

    db = SessionLocal()
    try:
        settings = BobUserSettings.get_or_create(db, user_id)

        # Update personality
        settings.tone = request.personality.tone
        settings.formality = request.personality.formality
        settings.response_length = request.personality.response_length
        settings.language = request.personality.language
        settings.creativity = request.personality.creativity
        settings.emoji_usage = request.personality.emoji_usage

        # Update voice
        settings.voice = request.voice.voice
        settings.speed = request.voice.speed
        settings.auto_listen = request.voice.auto_listen

        db.commit()
        db.refresh(settings)

        logger.info(
            "bob_settings_updated",
            user_id=user_id,
            tone=settings.tone,
            voice=settings.voice,
            speed=settings.speed,
        )

        return _db_to_response(settings)
    finally:
        db.close()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def reset_bob_settings(
    current_user: dict = Depends(get_current_user),
):
    """Reset Bob settings to defaults for the authenticated user."""
    user_id = current_user["user_id"]
    db = SessionLocal()
    try:
        settings = db.query(BobUserSettings).filter(BobUserSettings.user_id == user_id).first()
        if settings:
            db.delete(settings)
            db.commit()
        logger.info("bob_settings_reset", user_id=user_id)
    finally:
        db.close()
