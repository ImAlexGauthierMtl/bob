"""Tests for voice session management.

Note: Pipecat pipeline tests require the pipecat package installed.
The voice pipeline E2E test requires a real microphone and is manual.
These tests cover the session manager logic only.
"""

import time
import asyncio
import pytest


# ── Session unit tests ───────────────────────────────────────

class TestVoiceSession:
    """Tests for VoiceSession lifecycle."""

    def test_session_create(self):
        from app.voice.voice_session import VoiceSession
        session = VoiceSession(
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        assert session.session_id is not None
        assert session.user_id == "user-1"
        assert session.is_active is True
        assert session.turn_count == 0

    def test_session_record_turn(self):
        from app.voice.voice_session import VoiceSession
        session = VoiceSession(
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        session.record_turn()
        assert session.turn_count == 1

    def test_session_add_transcript(self):
        from app.voice.voice_session import VoiceSession
        session = VoiceSession(
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        session.add_transcript("user", "Hello Bob")
        session.add_transcript("assistant", "Hi there!")
        assert len(session.messages) == 2
        assert session.messages[0]["content"] == "Hello Bob"

    def test_session_expiry(self):
        from app.voice.voice_session import VoiceSession
        session = VoiceSession(
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
            max_duration_minutes=0,  # Instantly expires
        )
        assert session.is_expired() is True

    def test_session_not_expired(self):
        from app.voice.voice_session import VoiceSession
        session = VoiceSession(
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
            max_duration_minutes=60,
        )
        assert session.is_expired() is False

    def test_session_close(self):
        from app.voice.voice_session import VoiceSession
        session = VoiceSession(
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        session.record_turn()
        session.close()
        assert session.is_active is False

    def test_session_to_dict(self):
        from app.voice.voice_session import VoiceSession
        session = VoiceSession(
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        data = session.to_dict()
        assert data["user_id"] == "user-1"
        assert data["is_active"] is True
        assert "duration_seconds" in data


# ── Session Manager tests ────────────────────────────────────

class TestVoiceSessionManager:
    """Tests for VoiceSessionManager."""

    def setup_method(self):
        from app.voice.voice_session import VoiceSessionManager
        self.manager = VoiceSessionManager(max_concurrent=5)

    @pytest.mark.asyncio
    async def test_create_session(self):
        session = await self.manager.create_session(
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        assert session is not None
        assert session.is_active is True
        assert self.manager.get_active_count() == 1

    @pytest.mark.asyncio
    async def test_get_session(self):
        session = await self.manager.create_session(
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        retrieved = self.manager.get_session(session.session_id)
        assert retrieved is session

    @pytest.mark.asyncio
    async def test_close_session(self):
        session = await self.manager.create_session(
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        self.manager.close_session(session.session_id)
        assert self.manager.get_active_count() == 0
        assert self.manager.get_session(session.session_id) is None

    @pytest.mark.asyncio
    async def test_replace_existing_session(self):
        """Creating a new session for same user should close old one."""
        session1 = await self.manager.create_session(
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        session2 = await self.manager.create_session(
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        # Old session should be replaced
        assert session1.is_active is False
        assert session2.is_active is True
        assert self.manager.get_active_count() == 1

    @pytest.mark.asyncio
    async def test_multiple_users(self):
        """Different users should each get their own session."""
        await self.manager.create_session(
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="user1@croo.digital",
        )
        await self.manager.create_session(
            user_id="user-2",
            tenant_id="tenant-1",
            user_email="user2@croo.digital",
        )
        assert self.manager.get_active_count() == 2
