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
    language: str = Field(default="auto", description="Response language: auto, en, fr, es, de")
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

AVAILABLE_VOICES = [
    {"id": "autumn", "name": "Autumn", "gender": "female", "accent": "American", "style": "Warm & Natural"},
    {"id": "diana", "name": "Diana", "gender": "female", "accent": "American", "style": "Clear & Professional"},
    {"id": "hannah", "name": "Hannah", "gender": "female", "accent": "American", "style": "Friendly & Expressive"},
    {"id": "austin", "name": "Austin", "gender": "male", "accent": "American", "style": "Confident & Engaging"},
    {"id": "daniel", "name": "Daniel", "gender": "male", "accent": "American", "style": "Deep & Authoritative"},
    {"id": "troy", "name": "Troy", "gender": "male", "accent": "American", "style": "Energetic & Dynamic"},
]

AVAILABLE_TONES = ["professional", "friendly", "casual", "formal"]

AVAILABLE_LANGUAGES = [
    {"code": "auto", "name": "Auto-detect"},
    {"code": "en", "name": "English"},
    {"code": "fr", "name": "Français"},
    {"code": "es", "name": "Español"},
    {"code": "de", "name": "Deutsch"},
]


def _db_to_response(s: BobUserSettings) -> BobSettingsResponse:
    """Convert a DB row to the API response model."""
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
        available_voices=AVAILABLE_VOICES,
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

    # Validate voice exists
    valid_voice_ids = {v["id"] for v in AVAILABLE_VOICES}
    if request.voice.voice not in valid_voice_ids:
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
