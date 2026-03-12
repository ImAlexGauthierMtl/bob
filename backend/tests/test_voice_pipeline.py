"""Tests for voice pipeline — TTS character counting, session metrics."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestTTSCharacterCounter:
    """Test that TTSCharacterCounter accurately counts characters."""

    def test_voice_session_tts_counter_starts_at_zero(self):
        from app.voice.voice_session import VoiceSession

        session = VoiceSession(
            user_id="u1",
            tenant_id="t1",
            user_email="test@test.com",
        )
        assert session.tts_characters_total == 0

    def test_voice_session_metrics_include_tts(self):
        from app.voice.voice_session import VoiceSession

        session = VoiceSession(
            user_id="u1",
            tenant_id="t1",
            user_email="test@test.com",
        )
        session.tts_characters_total = 500
        session.turn_count = 3

        data = session.to_dict()
        assert data["tts_characters_total"] == 500
        assert data["turn_count"] == 3
        assert data["user_id"] == "u1"


class TestVoiceSessionLifecycle:
    """Test voice session creation, close, and cleanup."""

    def test_session_expiry(self):
        from app.voice.voice_session import VoiceSession
        import time

        session = VoiceSession(
            user_id="u1",
            tenant_id="t1",
            user_email="test@test.com",
            max_duration_minutes=0,
        )
        # With max_duration_minutes=0, session should be expired immediately
        assert session.is_expired()

    def test_session_close(self):
        from app.voice.voice_session import VoiceSession

        session = VoiceSession(
            user_id="u1",
            tenant_id="t1",
            user_email="test@test.com",
        )
        assert session.is_active
        session.close()
        assert not session.is_active

    def test_record_turn(self):
        from app.voice.voice_session import VoiceSession

        session = VoiceSession(
            user_id="u1",
            tenant_id="t1",
            user_email="test@test.com",
        )
        assert session.turn_count == 0
        session.record_turn()
        assert session.turn_count == 1

    def test_add_transcript(self):
        from app.voice.voice_session import VoiceSession

        session = VoiceSession(
            user_id="u1",
            tenant_id="t1",
            user_email="test@test.com",
        )
        session.add_transcript("user", "Hello Bob")
        session.add_transcript("assistant", "Hello! How can I help?")
        assert len(session.messages) == 2
        assert session.messages[0]["role"] == "user"
        assert session.messages[1]["content"] == "Hello! How can I help?"


class TestTTSTextCleaner:
    """Test that clean_text_for_tts strips formatting while preserving Orpheus tags."""

    def test_strips_markdown_bold(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        assert clean_text_for_tts("Here are **three** things") == "Here are three things"

    def test_strips_markdown_italic(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        assert clean_text_for_tts("This is *important*") == "This is important"

    def test_strips_markdown_headers(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        assert clean_text_for_tts("## My Header") == "My Header"

    def test_strips_markdown_bullets(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        result = clean_text_for_tts("- First item\n- Second item")
        assert "- " not in result
        assert "First item" in result

    def test_strips_numbered_lists(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        result = clean_text_for_tts("1. First\n2. Second")
        assert "1." not in result
        assert "First" in result

    def test_strips_urls(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        result = clean_text_for_tts("Visit https://example.com for more info")
        assert "https://" not in result
        assert "Visit" in result

    def test_strips_markdown_links(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        result = clean_text_for_tts("Check [this page](https://example.com)")
        assert result == "Check this page"

    def test_strips_backticks(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        result = clean_text_for_tts("Use the `navigate_to` function")
        assert "`" not in result
        assert "navigate_to" in result

    def test_strips_emoji(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        result = clean_text_for_tts("Great job! 🎉 Keep going 🚀")
        assert "🎉" not in result
        assert "🚀" not in result
        assert "Great job" in result

    def test_normalizes_ellipsis(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        result = clean_text_for_tts("Well... let me think")
        assert "..." not in result
        assert "Well" in result

    def test_normalizes_em_dash(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        result = clean_text_for_tts("This is important — really important")
        assert "—" not in result
        assert "important" in result

    def test_strips_parenthetical_asides(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        result = clean_text_for_tts("Use tools (e.g., navigate_to) to help")
        assert "(e.g." not in result

    def test_preserves_orpheus_emotion_tags(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        text = "That's great <laugh> I love it"
        result = clean_text_for_tts(text, preserve_orpheus_tags=True)
        assert "<laugh>" in result
        assert "I love it" in result

    def test_preserves_orpheus_chuckle(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        text = "Interesting question <chuckle> let me check"
        result = clean_text_for_tts(text, preserve_orpheus_tags=True)
        assert "<chuckle>" in result

    def test_preserves_orpheus_sigh(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        text = "I understand <sigh> that's frustrating"
        result = clean_text_for_tts(text, preserve_orpheus_tags=True)
        assert "<sigh>" in result

    def test_preserves_vocal_directions(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        text = "[cheerful] Sure thing, I've opened the page"
        result = clean_text_for_tts(text, preserve_orpheus_tags=True)
        assert "[cheerful]" in result
        assert "Sure thing" in result

    def test_preserves_whisper_direction(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        text = "[whisper] This is a secret"
        result = clean_text_for_tts(text, preserve_orpheus_tags=True)
        assert "[whisper]" in result

    def test_strips_orpheus_tags_when_not_orpheus(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        text = "That's great <laugh> I love it [cheerful] yes"
        result = clean_text_for_tts(text, preserve_orpheus_tags=False)
        assert "<laugh>" not in result
        assert "[cheerful]" not in result
        assert "great" in result

    def test_combined_markdown_and_orpheus(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        text = "**Great** question <chuckle> let me check the `contacts` page"
        result = clean_text_for_tts(text, preserve_orpheus_tags=True)
        assert "**" not in result
        assert "`" not in result
        assert "<chuckle>" in result
        assert "Great question" in result

    def test_empty_string(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        assert clean_text_for_tts("") == ""

    def test_plain_text_unchanged(self):
        from app.voice.tts_text_cleaner import clean_text_for_tts
        text = "Hello, how can I help you today?"
        assert clean_text_for_tts(text) == text


class TestSeedRateCards:
    """Test that rate cards include the correct TTS model."""

    def test_orpheus_rate_card_exists(self):
        from app.infrastructure.seed_rate_cards import RATE_CARDS

        orpheus_cards = [c for c in RATE_CARDS if c["model"] == "canopylabs/orpheus-v1-english"]
        assert len(orpheus_cards) == 1
        assert orpheus_cards[0]["service_type"].value == "tts"
