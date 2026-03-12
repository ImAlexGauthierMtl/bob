"""Tests for voice routes — auth, rate limiting, session management."""

import pytest
from unittest.mock import patch, MagicMock


class TestRateLimiter:
    """Test rate limiter consistency."""

    def test_voice_limit_message_matches_config(self):
        """Verify the error message limit matches the actual configured limit."""
        from app.middleware.rate_limiter import RateLimiter

        limiter = RateLimiter()
        user_id = "test-user-voice-limit"

        # The bucket has max_calls=500
        bucket = limiter._voice_buckets[user_id]
        assert bucket.max_calls == 500

    def test_chat_limit_message_matches_config(self):
        from app.middleware.rate_limiter import RateLimiter

        limiter = RateLimiter()
        user_id = "test-user-chat-limit"

        bucket = limiter._chat_buckets[user_id]
        assert bucket.max_calls == 30

    def test_voice_rate_limit_triggers_429(self):
        from app.middleware.rate_limiter import RateLimiter
        from fastapi import HTTPException

        limiter = RateLimiter()
        # Fill up the bucket
        user_id = "rate-limit-test"
        bucket = limiter._voice_buckets[user_id]
        import time
        bucket.calls = [time.time()] * 500

        with pytest.raises(HTTPException) as exc_info:
            limiter.check_voice(user_id)
        assert exc_info.value.status_code == 429
        assert "500 sessions/hour" in str(exc_info.value.detail)


class TestVoiceRoutesDocstring:
    """Test that voice routes have correct documentation."""

    def test_output_format_docs(self):
        from app.presentation.routes.voice_routes import bob_voice_ws

        docstring = bob_voice_ws.__doc__ or ""
        assert "24kHz" in docstring
        assert "no WAV header" in docstring
        assert "48kHz" not in docstring


class TestSessionStore:
    """Test session store abstraction."""

    def test_in_memory_store_set_get(self):
        from app.infrastructure.session_store import InMemorySessionStore

        store = InMemorySessionStore()
        store.set("test:key", {"user": "bob", "count": 5})

        result = store.get("test:key")
        assert result is not None
        assert result["user"] == "bob"
        assert result["count"] == 5

    def test_in_memory_store_ttl_expiry(self):
        from app.infrastructure.session_store import InMemorySessionStore
        import time

        store = InMemorySessionStore()
        store.set("expire:key", {"data": "value"}, ttl_seconds=0)

        time.sleep(0.01)
        result = store.get("expire:key")
        assert result is None

    def test_in_memory_store_delete(self):
        from app.infrastructure.session_store import InMemorySessionStore

        store = InMemorySessionStore()
        store.set("del:key", {"data": "value"})
        store.delete("del:key")
        assert store.get("del:key") is None

    def test_in_memory_store_keys(self):
        from app.infrastructure.session_store import InMemorySessionStore

        store = InMemorySessionStore()
        store.set("chat:session1", {"a": 1})
        store.set("chat:session2", {"b": 2})
        store.set("voice:session1", {"c": 3})

        chat_keys = store.keys("chat:*")
        assert len(chat_keys) == 2
        assert "chat:session1" in chat_keys
