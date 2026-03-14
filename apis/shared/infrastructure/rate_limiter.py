"""Rate limiter — sliding window per user."""

import time
from collections import defaultdict
from fastapi import HTTPException, status
from .logging import get_logger

logger = get_logger(__name__)


class _UserBucket:
    """Sliding window counter for a single user."""

    __slots__ = ("calls", "window_seconds", "max_calls")

    def __init__(self, max_calls: int, window_seconds: int):
        self.calls: list[float] = []
        self.window_seconds = window_seconds
        self.max_calls = max_calls

    def allow(self) -> bool:
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
    """Per-user rate limiter with configurable limits.

    Usage:
        limiter = RateLimiter()
        limiter.check("chat", user_id, max_calls=30, window_seconds=60)
    """

    def __init__(self):
        self._buckets: dict[str, dict[str, _UserBucket]] = defaultdict(dict)

    def check(
        self,
        endpoint: str,
        user_id: str,
        max_calls: int = 30,
        window_seconds: int = 60,
    ) -> None:
        """Check rate limit. Raises 429 if exceeded."""
        if user_id not in self._buckets[endpoint]:
            self._buckets[endpoint][user_id] = _UserBucket(max_calls, window_seconds)

        bucket = self._buckets[endpoint][user_id]
        if not bucket.allow():
            logger.warning(
                "rate_limit_exceeded",
                user_id=user_id,
                endpoint=endpoint,
                reset_seconds=bucket.reset_seconds,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after_seconds": bucket.reset_seconds,
                    "limit": f"{max_calls} requests/{window_seconds}s",
                },
            )

    def get_remaining(self, endpoint: str, user_id: str) -> int:
        if user_id in self._buckets.get(endpoint, {}):
            return self._buckets[endpoint][user_id].remaining
        return 0


# Singleton
rate_limiter = RateLimiter()
