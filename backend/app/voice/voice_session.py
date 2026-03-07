"""Voice session management — lifecycle, state, and cleanup.

Each WebSocket connection creates a VoiceSession that tracks
conversation state, metrics, and handles TTL-based expiry.
"""

import asyncio
import time
import uuid
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class VoiceSession:
    """A single user's voice session with Bob."""

    def __init__(
        self,
        user_id: str,
        tenant_id: str,
        user_email: str,
        max_duration_minutes: int = 30,
    ):
        self.session_id = str(uuid.uuid4())
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.user_email = user_email
        self.max_duration_minutes = max_duration_minutes

        self.created_at = time.time()
        self.last_activity = time.time()
        self.is_active = True

        # Metrics
        self.turn_count = 0
        self.total_audio_seconds = 0.0
        self.total_stt_calls = 0
        self.total_tts_calls = 0
        self.total_llm_calls = 0

        # Conversation context for the LLM
        self.messages: list[dict[str, str]] = []

        logger.info(
            "voice_session_created",
            session_id=self.session_id,
            user=user_email,
        )

    def record_turn(self) -> None:
        """Record a completed voice turn (user spoke → Bob responded)."""
        self.turn_count += 1
        self.last_activity = time.time()

    def add_transcript(self, role: str, text: str) -> None:
        """Add a transcript to the conversation history."""
        self.messages.append({"role": role, "content": text})
        self.last_activity = time.time()

    def is_expired(self) -> bool:
        """Check if session has exceeded max duration."""
        elapsed = time.time() - self.created_at
        return elapsed > (self.max_duration_minutes * 60)

    def close(self) -> None:
        """Mark session as closed and log metrics."""
        self.is_active = False
        duration = time.time() - self.created_at

        logger.info(
            "voice_session_closed",
            session_id=self.session_id,
            user=self.user_email,
            duration_seconds=round(duration, 1),
            turns=self.turn_count,
            stt_calls=self.total_stt_calls,
            tts_calls=self.total_tts_calls,
            llm_calls=self.total_llm_calls,
        )

    def to_dict(self) -> dict:
        """Return session metadata as dict."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "is_active": self.is_active,
            "turn_count": self.turn_count,
            "created_at": self.created_at,
            "duration_seconds": round(time.time() - self.created_at, 1),
        }


class VoiceSessionManager:
    """Manages active voice sessions with concurrency control."""

    def __init__(self, max_concurrent: int = 10):
        self._sessions: dict[str, VoiceSession] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent

    async def create_session(
        self,
        user_id: str,
        tenant_id: str,
        user_email: str,
        max_duration_minutes: int = 30,
    ) -> VoiceSession:
        """Create a new voice session, respecting concurrency limits."""
        # Check if user already has an active session
        for session in self._sessions.values():
            if session.user_id == user_id and session.is_active:
                logger.warning(
                    "voice_session_already_active",
                    user=user_email,
                    existing_session=session.session_id,
                )
                # Close the old session
                session.close()
                del self._sessions[session.session_id]
                break

        session = VoiceSession(
            user_id=user_id,
            tenant_id=tenant_id,
            user_email=user_email,
            max_duration_minutes=max_duration_minutes,
        )
        self._sessions[session.session_id] = session

        logger.info(
            "voice_sessions_active",
            count=len(self._sessions),
            max=self._max_concurrent,
        )

        return session

    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> None:
        """Close and remove a session."""
        session = self._sessions.get(session_id)
        if session:
            session.close()
            del self._sessions[session_id]

    def get_active_count(self) -> int:
        """Get number of active sessions."""
        return len(self._sessions)

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Semaphore for concurrency control."""
        return self._semaphore


# Singleton
voice_session_manager = VoiceSessionManager()
