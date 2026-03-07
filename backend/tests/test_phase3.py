"""Tests for Phase 3 enterprise hardening — rate limiter + cost tracker."""

import pytest
from fastapi import HTTPException


class TestRateLimiterBucket:
    """Tests for the internal _UserBucket."""

    def test_bucket_allows_within_limit(self):
        from app.middleware.rate_limiter import _UserBucket
        bucket = _UserBucket(max_calls=5, window_seconds=60)
        for _ in range(5):
            assert bucket.allow() is True
        assert bucket.allow() is False

    def test_bucket_remaining(self):
        from app.middleware.rate_limiter import _UserBucket
        bucket = _UserBucket(max_calls=10, window_seconds=60)
        bucket.allow()
        bucket.allow()
        assert bucket.remaining == 8

    def test_bucket_reset_seconds(self):
        from app.middleware.rate_limiter import _UserBucket
        bucket = _UserBucket(max_calls=1, window_seconds=60)
        bucket.allow()
        assert bucket.reset_seconds > 0


class TestRateLimiter:
    """Tests for the RateLimiter singleton."""

    def setup_method(self):
        from app.middleware.rate_limiter import RateLimiter
        self.limiter = RateLimiter()

    def test_chat_within_limit(self):
        """Should not raise for normal usage."""
        self.limiter.check_chat("user-1")  # Should not raise

    def test_chat_exceeds_limit(self):
        """Should raise 429 after exceeding limit."""
        for i in range(30):
            self.limiter.check_chat("user-rate-test")
        with pytest.raises(HTTPException) as exc_info:
            self.limiter.check_chat("user-rate-test")
        assert exc_info.value.status_code == 429

    def test_voice_within_limit(self):
        """Should not raise for normal voice usage."""
        self.limiter.check_voice("user-1")  # Should not raise

    def test_voice_exceeds_limit(self):
        """Should raise 429 after exceeding voice limit."""
        for i in range(5):
            self.limiter.check_voice("user-voice-test")
        with pytest.raises(HTTPException) as exc_info:
            self.limiter.check_voice("user-voice-test")
        assert exc_info.value.status_code == 429

    def test_separate_users(self):
        """Different users should have independent limits."""
        for i in range(30):
            self.limiter.check_chat("user-a")
        # user-b should still be fine
        self.limiter.check_chat("user-b")

    def test_remaining_counts(self):
        """Should report correct remaining counts."""
        assert self.limiter.get_chat_remaining("user-fresh") == 30
        self.limiter.check_chat("user-fresh")
        assert self.limiter.get_chat_remaining("user-fresh") == 29


class TestCostTracker:
    """Tests for the CostTracker."""

    def setup_method(self):
        from app.middleware.cost_tracker import CostTracker
        self.tracker = CostTracker()

    def test_log_llm_call(self):
        record = self.tracker.log_llm_call(
            model="qwen3-32b",
            user_id="user-1",
            session_id="session-1",
            input_tokens=100,
            output_tokens=50,
            duration_ms=250.0,
        )
        assert record.service == "llm"
        assert record.input_tokens == 100
        assert record.estimated_cost_usd > 0

    def test_log_stt_call(self):
        record = self.tracker.log_stt_call(
            model="whisper-large-v3-turbo",
            user_id="user-1",
            session_id="session-1",
            audio_seconds=5.0,
            duration_ms=800.0,
        )
        assert record.service == "stt"
        assert record.audio_seconds == 5.0
        assert record.estimated_cost_usd >= 0

    def test_log_tts_call(self):
        record = self.tracker.log_tts_call(
            model="playai-tts",
            user_id="user-1",
            session_id="session-1",
            characters=100,
            duration_ms=300.0,
        )
        assert record.service == "tts"
        assert record.characters == 100

    def test_user_total(self):
        self.tracker.log_llm_call(
            model="qwen3-32b",
            user_id="user-total",
            session_id="s1",
            input_tokens=100,
            output_tokens=50,
            duration_ms=200.0,
        )
        self.tracker.log_stt_call(
            model="whisper-large-v3-turbo",
            user_id="user-total",
            session_id="s1",
            audio_seconds=3.0,
            duration_ms=500.0,
        )
        totals = self.tracker.get_user_total("user-total")
        assert totals["total_calls"] == 2
        assert totals["breakdown"]["llm"] == 1
        assert totals["breakdown"]["stt"] == 1

    def test_session_total(self):
        self.tracker.log_llm_call(
            model="qwen3-32b",
            user_id="u1",
            session_id="session-x",
            input_tokens=50,
            output_tokens=25,
            duration_ms=100.0,
        )
        totals = self.tracker.get_session_total("session-x")
        assert totals["total_calls"] == 1
        assert totals["total_estimated_cost_usd"] >= 0


class TestBobTools:
    """Tests for Bob CRM tool definitions."""

    def test_tool_definitions_format(self):
        from app.agents.bob_tools import BOB_TOOLS
        assert len(BOB_TOOLS) == 6
        for tool in BOB_TOOLS:
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]

    def test_tool_names(self):
        from app.agents.bob_tools import BOB_TOOLS
        names = {t["function"]["name"] for t in BOB_TOOLS}
        assert "search_contacts" in names
        assert "search_organizations" in names
        assert "get_pipeline_stats" in names
        assert "create_contact" in names
        assert "create_organization" in names
        assert "get_recent_activities" in names
