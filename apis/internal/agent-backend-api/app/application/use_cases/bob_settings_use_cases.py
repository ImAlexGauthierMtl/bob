"""Bob settings application use cases."""
from dataclasses import dataclass
from typing import Any, Protocol

import structlog

from app.domain.exceptions import InvalidBobToneError, InvalidBobVoiceError

logger = structlog.get_logger(__name__)


_QWEN_FEMALE_WARM = [
    {"id": "Cherry", "name": "Cherry", "gender": "female", "style": "Chaleureuse & Naturelle"},
    {"id": "Serena", "name": "Serena", "gender": "female", "style": "Douce & Intentionnelle"},
    {"id": "Maia", "name": "Maia", "gender": "female", "style": "Intelligente & Douce"},
    {"id": "Mia", "name": "Mia", "gender": "female", "style": "Apaisante & Délicate"},
    {"id": "Vivian", "name": "Vivian", "gender": "female", "style": "Confiante & Espiègle"},
    {"id": "Momo", "name": "Momo", "gender": "female", "style": "Enjouée & Pétillante"},
]

_QWEN_FEMALE_PRO = [
    {"id": "Jennifer", "name": "Jennifer", "gender": "female", "style": "Cinématique & Premium"},
    {"id": "Katerina", "name": "Katerina", "gender": "female", "style": "Posée & Mémorable"},
    {"id": "Elias", "name": "Elias", "gender": "female", "style": "Académique & Précise"},
    {"id": "Bellona", "name": "Bellona", "gender": "female", "style": "Puissante & Théâtrale"},
    {"id": "Bella", "name": "Bella", "gender": "female", "style": "Légère & Pétillante"},
]

_QWEN_MALE_WARM = [
    {"id": "Ethan", "name": "Ethan", "gender": "male", "style": "Solaire & Énergique"},
    {"id": "Aiden", "name": "Aiden", "gender": "male", "style": "Décontracté & Accessible"},
    {"id": "Mochi", "name": "Mochi", "gender": "male", "style": "Vif & Espiègle"},
    {"id": "Kai", "name": "Kai", "gender": "male", "style": "Apaisant & Enveloppant"},
    {"id": "Moon", "name": "Moon", "gender": "male", "style": "Audacieux & Charismatique"},
]

_QWEN_MALE_PRO = [
    {"id": "Ryan", "name": "Ryan", "gender": "male", "style": "Dramatique & Expressif"},
    {"id": "Neil", "name": "Neil", "gender": "male", "style": "Articulé & Journalistique"},
    {"id": "Vincent", "name": "Vincent", "gender": "male", "style": "Rauque & Cinématique"},
    {"id": "Arthur", "name": "Arthur", "gender": "male", "style": "Rustique & Chaleureux"},
    {"id": "Eldric Sage", "name": "Eldric Sage", "gender": "male", "style": "Sage & Posé"},
]

_QWEN_CUSTOM = [
    {"id": "Rick", "name": "Rick ⭐", "gender": "male", "style": "Voix clonée — Ricardo"},
]


def _build_voice_list(voices: list[dict[str, Any]], accent: str, provider: str = "qwen") -> list[dict[str, Any]]:
    return [{**voice, "accent": accent, "provider": provider} for voice in voices]


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

ORPHEUS_VOICES = [
    {"id": "autumn", "name": "Autumn", "gender": "female", "accent": "American", "style": "Warm & Natural", "provider": "orpheus"},
    {"id": "diana", "name": "Diana", "gender": "female", "accent": "American", "style": "Clear & Professional", "provider": "orpheus"},
    {"id": "hannah", "name": "Hannah", "gender": "female", "accent": "American", "style": "Friendly & Expressive", "provider": "orpheus"},
    {"id": "austin", "name": "Austin", "gender": "male", "accent": "American", "style": "Confident & Engaging", "provider": "orpheus"},
    {"id": "daniel", "name": "Daniel", "gender": "male", "accent": "American", "style": "Deep & Authoritative", "provider": "orpheus"},
    {"id": "troy", "name": "Troy", "gender": "male", "accent": "American", "style": "Energetic & Dynamic", "provider": "orpheus"},
]

QWEN_LANGUAGE_CODES = {"fr", "fr-FR", "fr-CA", "es", "pt"}
AVAILABLE_TONES = ["professional", "friendly", "casual", "formal"]
AVAILABLE_LANGUAGES = [
    {"code": "auto", "name": "Auto-detect"},
    {"code": "en", "name": "English"},
    {"code": "fr-CA", "name": "Français (Canada / Québec)"},
    {"code": "fr-FR", "name": "Français (France)"},
    {"code": "es", "name": "Español"},
    {"code": "pt", "name": "Português"},
]


class BobSettingsRepositoryPort(Protocol):
    def get_or_create(self, user_id: str, tenant_id: str) -> Any:
        ...

    def save(self, settings: Any) -> Any:
        ...

    def reset(self, user_id: str) -> None:
        ...


@dataclass(frozen=True)
class BobSettingsView:
    personality: dict[str, Any]
    voice: dict[str, Any]
    available_voices: list[dict[str, Any]]
    available_tones: list[str]
    available_languages: list[dict[str, Any]]


class BobSettingsUseCases:
    def __init__(self, repo: BobSettingsRepositoryPort) -> None:
        self.repo = repo

    async def get_settings(self, user: dict[str, Any]) -> BobSettingsView:
        settings = self.repo.get_or_create(user["user_id"], user["tenant_id"])
        return self._to_view(settings)

    async def update_settings(self, request: dict[str, Any], user: dict[str, Any]) -> BobSettingsView:
        personality = request["personality"]
        voice = request["voice"]
        self._validate_voice(voice["voice"])
        self._validate_tone(personality["tone"])

        settings = self.repo.get_or_create(user["user_id"], user["tenant_id"])
        settings.tone = personality["tone"]
        settings.formality = personality["formality"]
        settings.response_length = personality["response_length"]
        settings.language = personality["language"]
        settings.creativity = personality["creativity"]
        settings.emoji_usage = personality["emoji_usage"]
        settings.voice = voice["voice"]
        settings.speed = voice["speed"]
        settings.auto_listen = voice["auto_listen"]

        settings = self.repo.save(settings)
        logger.info("bob_settings_updated", user_id=user["user_id"], tone=settings.tone, voice=settings.voice)
        return self._to_view(settings)

    async def reset_settings(self, user: dict[str, Any]) -> None:
        self.repo.reset(user["user_id"])
        logger.info("bob_settings_reset", user_id=user["user_id"])

    def _validate_voice(self, voice: str) -> None:
        all_qwen_voice_ids = {v["id"] for v in QWEN_VOICES_FR_CA + QWEN_VOICES_FR_FR + QWEN_VOICES_INTL}
        all_voice_ids = {v["id"] for v in ORPHEUS_VOICES} | all_qwen_voice_ids
        if voice not in all_voice_ids:
            raise InvalidBobVoiceError(voice)

    def _validate_tone(self, tone: str) -> None:
        if tone not in AVAILABLE_TONES:
            raise InvalidBobToneError(tone)

    def _to_view(self, settings: Any) -> BobSettingsView:
        return BobSettingsView(
            personality={
                "tone": settings.tone,
                "formality": settings.formality,
                "response_length": settings.response_length,
                "language": settings.language,
                "creativity": settings.creativity,
                "emoji_usage": settings.emoji_usage,
            },
            voice={
                "voice": settings.voice,
                "speed": settings.speed,
                "auto_listen": settings.auto_listen,
            },
            available_voices=self._voices_for_language(settings.language),
            available_tones=AVAILABLE_TONES,
            available_languages=AVAILABLE_LANGUAGES,
        )

    def _voices_for_language(self, language: str) -> list[dict[str, Any]]:
        if language == "fr-CA":
            return QWEN_VOICES_FR_CA
        if language == "fr-FR":
            return QWEN_VOICES_FR_FR
        if language in QWEN_LANGUAGE_CODES:
            return QWEN_VOICES_INTL
        return ORPHEUS_VOICES
