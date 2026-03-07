"""Rate limiter — per-user token bucket for Bob API calls.

Uses in-memory sliding window counters. For production scale,
swap to Redis-backed implementation.
"""

import time
from collections import defaultdict
from typing import Optional

import structlog
from fastapi import HTTPException, Request, status

from app.config import settings

logger = structlog.get_logger(__name__)


class _UserBucket:
    """Sliding window counter for a single user."""

    __slots__ = ("calls", "window_seconds", "max_calls")

    def __init__(self, max_calls: int, window_seconds: int):
        self.calls: list[float] = []
        self.window_seconds = window_seconds
        self.max_calls = max_calls

    def allow(self) -> bool:
        """Check if a new call is allowed, pruning expired entries."""
        now = time.time()
        cutoff = now - self.window_seconds
        self.calls = [t for t in self.calls if t > cutoff]
        if len(self.calls) >= self.max_calls:
            return False
        self.calls.append(now)
        return True

    @property
    def remaining(self) -> int:
        now = time.time()
        cutoff = now - self.window_seconds
        active = sum(1 for t in self.calls if t > cutoff)
        return max(0, self.max_calls - active)

    @property
    def reset_seconds(self) -> int:
        if not self.calls:
            return 0
        return max(0, int(self.calls[0] + self.window_seconds - time.time()))


class RateLimiter:
    """Per-user rate limiter with configurable limits per endpoint type."""

    def __init__(self):
        # Bob chat: 30 requests/minute per user
        self._chat_buckets: dict[str, _UserBucket] = defaultdict(
            lambda: _UserBucket(max_calls=30, window_seconds=60)
        )
        # Voice sessions: 5 new sessions/hour per user
        self._voice_buckets: dict[str, _UserBucket] = defaultdict(
            lambda: _UserBucket(max_calls=5, window_seconds=3600)
        )

    def check_chat(self, user_id: str) -> None:
        """Check rate limit for chat endpoint. Raises 429 if exceeded."""
        bucket = self._chat_buckets[user_id]
        if not bucket.allow():
            logger.warning(
                "rate_limit_exceeded",
                user_id=user_id,
                endpoint="chat",
                reset_seconds=bucket.reset_seconds,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after_seconds": bucket.reset_seconds,
                    "limit": "30 requests/minute",
                },
            )

    def check_voice(self, user_id: str) -> None:
        """Check rate limit for voice session creation. Raises 429 if exceeded."""
        bucket = self._voice_buckets[user_id]
        if not bucket.allow():
            logger.warning(
                "rate_limit_exceeded",
                user_id=user_id,
                endpoint="voice",
                reset_seconds=bucket.reset_seconds,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded for voice sessions",
                    "retry_after_seconds": bucket.reset_seconds,
                    "limit": "5 sessions/hour",
                },
            )

    def get_chat_remaining(self, user_id: str) -> int:
        """Get remaining chat calls for a user."""
        return self._chat_buckets[user_id].remaining

    def get_voice_remaining(self, user_id: str) -> int:
        """Get remaining voice session calls for a user."""
        return self._voice_buckets[user_id].remaining


# Singleton
rate_limiter = RateLimiter()
