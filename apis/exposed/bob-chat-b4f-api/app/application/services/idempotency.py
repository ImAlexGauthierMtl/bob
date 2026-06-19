"""In-memory idempotency boundary for the Bob Chat B4F facade.

This is deliberately scoped to the B4F facade until the conversation/runtime
backends own durable deduplication.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Optional


class IdempotencyConflictError(ValueError):
    """Raised when an idempotency key is reused with a different payload."""


@dataclass
class IdempotencyRecord:
    payload_hash: str
    response: dict[str, Any]
    expires_at: float


class InMemoryIdempotencyStore:
    def __init__(self, ttl_seconds: int = 86400) -> None:
        self.ttl_seconds = ttl_seconds
        self._records: dict[str, IdempotencyRecord] = {}

    def get(self, key: str, payload_hash: str, now: Optional[float] = None) -> Optional[dict[str, Any]]:
        checked_at = now or time.time()
        self._cleanup(checked_at)
        record = self._records.get(key)
        if not record:
            return None
        if record.payload_hash != payload_hash:
            raise IdempotencyConflictError("Idempotency key reused with a different payload")
        return record.response

    def store(self, key: str, payload_hash: str, response: dict[str, Any], now: Optional[float] = None) -> None:
        created_at = now or time.time()
        self._records[key] = IdempotencyRecord(
            payload_hash=payload_hash,
            response=response,
            expires_at=created_at + self.ttl_seconds,
        )

    def clear(self) -> None:
        self._records.clear()

    def _cleanup(self, now: float) -> None:
        expired = [key for key, record in self._records.items() if record.expires_at <= now]
        for key in expired:
            del self._records[key]
