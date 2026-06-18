"""Bob settings routes — user-level Bob personality and voice configuration.

Pure CRUD — stores per-user Bob settings in the database.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.application.use_cases.bob_settings_use_cases import BobSettingsUseCases, BobSettingsView
from app.domain.exceptions import InvalidBobToneError, InvalidBobVoiceError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_bob_settings_use_cases

router = APIRouter(prefix="/api/v1/bob/settings")


# ── Schemas ──────────────────────────────────────

class BobPersonality(BaseModel):
    tone: str = Field(default="professional")
    formality: float = Field(default=0.5, ge=0.0, le=1.0)
    response_length: str = Field(default="balanced")
    language: str = Field(default="auto")
    creativity: float = Field(default=0.3, ge=0.0, le=1.0)
    emoji_usage: bool = Field(default=False)


class BobVoiceSettings(BaseModel):
    voice: str = Field(default="autumn")
    speed: float = Field(default=1.0, ge=0.5, le=3.0)
    auto_listen: bool = Field(default=True)


class BobSettingsRequest(BaseModel):
    personality: BobPersonality = Field(default_factory=BobPersonality)
    voice: BobVoiceSettings = Field(default_factory=BobVoiceSettings)


class BobSettingsResponse(BaseModel):
    personality: BobPersonality
    voice: BobVoiceSettings
    available_voices: list[dict]
    available_tones: list[str]
    available_languages: list[dict]


def _view_to_response(view: BobSettingsView) -> BobSettingsResponse:
    return BobSettingsResponse(
        personality=BobPersonality(**view.personality),
        voice=BobVoiceSettings(**view.voice),
        available_voices=view.available_voices,
        available_tones=view.available_tones,
        available_languages=view.available_languages,
    )


# ── Routes ───────────────────────────────────────

@router.get("", response_model=BobSettingsResponse)
async def get_bob_settings(
    current_user: dict = Depends(get_current_user),
    use_cases: BobSettingsUseCases = Depends(get_bob_settings_use_cases),
):
    return _view_to_response(await use_cases.get_settings(current_user))


@router.put("", response_model=BobSettingsResponse)
async def update_bob_settings(
    request: BobSettingsRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: BobSettingsUseCases = Depends(get_bob_settings_use_cases),
):
    try:
        view = await use_cases.update_settings(request.model_dump(), current_user)
    except InvalidBobVoiceError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid voice: {request.voice.voice}")
    except InvalidBobToneError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid tone: {request.personality.tone}")
    return _view_to_response(view)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def reset_bob_settings(
    current_user: dict = Depends(get_current_user),
    use_cases: BobSettingsUseCases = Depends(get_bob_settings_use_cases),
):
    await use_cases.reset_settings(current_user)
