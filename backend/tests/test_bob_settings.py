"""Tests for Bob settings routes — GET/PUT/DELETE personality & voice config."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


# ── Unit tests for settings logic ────────────────────────────

class TestBobSettingsSchemas:
    """Tests for settings Pydantic models."""

    def test_default_personality(self):
        from app.presentation.routes.bob_settings_routes import BobPersonality
        p = BobPersonality()
        assert p.tone == "professional"
        assert p.formality == 0.5
        assert p.response_length == "balanced"
        assert p.creativity == 0.3
        assert p.emoji_usage is False

    def test_default_voice(self):
        from app.presentation.routes.bob_settings_routes import BobVoiceSettings
        v = BobVoiceSettings()
        assert v.voice == "autumn"
        assert v.speed == 1.0
        assert v.auto_listen is True

    def test_personality_bounds(self):
        from app.presentation.routes.bob_settings_routes import BobPersonality
        # formality clamped 0-1
        with pytest.raises(Exception):
            BobPersonality(formality=1.5)
        with pytest.raises(Exception):
            BobPersonality(formality=-0.1)

    def test_voice_speed_bounds(self):
        from app.presentation.routes.bob_settings_routes import BobVoiceSettings
        with pytest.raises(Exception):
            BobVoiceSettings(speed=0.1)  # below 0.5
        with pytest.raises(Exception):
            BobVoiceSettings(speed=5.0)  # above 3.0


class TestBobSettingsAvailableOptions:
    """Tests for available options constants."""

    def test_voices_count(self):
        from app.presentation.routes.bob_settings_routes import AVAILABLE_VOICES
        assert len(AVAILABLE_VOICES) == 6

    def test_voice_structure(self):
        from app.presentation.routes.bob_settings_routes import AVAILABLE_VOICES
        for v in AVAILABLE_VOICES:
            assert "id" in v
            assert "name" in v
            assert "gender" in v
            assert "accent" in v
            assert "style" in v

    def test_tones(self):
        from app.presentation.routes.bob_settings_routes import AVAILABLE_TONES
        assert "professional" in AVAILABLE_TONES
        assert "friendly" in AVAILABLE_TONES
        assert "casual" in AVAILABLE_TONES
        assert "formal" in AVAILABLE_TONES

    def test_languages(self):
        from app.presentation.routes.bob_settings_routes import AVAILABLE_LANGUAGES
        codes = [l["code"] for l in AVAILABLE_LANGUAGES]
        assert "auto" in codes
        assert "en" in codes
        assert "fr" in codes


class TestBobSettingsRequest:
    """Tests for BobSettingsRequest model."""

    def test_default_request(self):
        from app.presentation.routes.bob_settings_routes import BobSettingsRequest
        req = BobSettingsRequest()
        assert req.personality.tone == "professional"
        assert req.voice.voice == "autumn"

    def test_custom_request(self):
        from app.presentation.routes.bob_settings_routes import BobSettingsRequest
        req = BobSettingsRequest(
            personality={"tone": "casual", "creativity": 0.8},
            voice={"voice": "Celeste-PlayAI", "speed": 1.5},
        )
        assert req.personality.tone == "casual"
        assert req.personality.creativity == 0.8
        assert req.voice.voice == "Celeste-PlayAI"
        assert req.voice.speed == 1.5
