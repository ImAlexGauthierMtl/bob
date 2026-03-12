"""Session store — Redis-backed with in-memory fallback.

Provides a unified interface for persisting chat and voice sessions
with TTL-based expiry. Falls back to in-memory dict when Redis is unavailable.
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class SessionStore(ABC):
    """Abstract session store interface."""

    @abstractmethod
    def get(self, key: str) -> dict | None:
        ...

    @abstractmethod
    def set(self, key: str, data: dict, ttl_seconds: int | None = None) -> None:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...

    @abstractmethod
    def keys(self, pattern: str) -> list[str]:
        ...


class InMemorySessionStore(SessionStore):
    """Fallback in-memory store with manual TTL expiry."""

    def __init__(self):
        self._store: dict[str, dict[str, Any]] = {}

    def _prune_expired(self):
        now = time.time()
        expired = [
            k for k, v in self._store.items()
            if v.get("_expires_at") and v["_expires_at"] < now
        ]
        for k in expired:
            del self._store[k]

    def get(self, key: str) -> dict | None:
        self._prune_expired()
        entry = self._store.get(key)
        if entry is None:
            return None
        result = {k: v for k, v in entry.items() if not k.startswith("_")}
        return result

    def set(self, key: str, data: dict, ttl_seconds: int | None = None) -> None:
        entry = dict(data)
        if ttl_seconds:
            entry["_expires_at"] = time.time() + ttl_seconds
        self._store[key] = entry

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def exists(self, key: str) -> bool:
        self._prune_expired()
        return key in self._store

    def keys(self, pattern: str) -> list[str]:
        self._prune_expired()
        prefix = pattern.rstrip("*")
        return [k for k in self._store if k.startswith(prefix)]


class RedisSessionStore(SessionStore):
    """Redis-backed store with native TTL."""

    def __init__(self, redis_url: str):
        import redis
        self._redis = redis.from_url(redis_url, decode_responses=True)
        logger.info("redis_session_store_connected", url=redis_url.split("@")[-1])

    def get(self, key: str) -> dict | None:
        raw = self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def set(self, key: str, data: dict, ttl_seconds: int | None = None) -> None:
        raw = json.dumps(data, default=str)
        if ttl_seconds:
            self._redis.setex(key, ttl_seconds, raw)
        else:
            self._redis.set(key, raw)

    def delete(self, key: str) -> None:
        self._redis.delete(key)

    def exists(self, key: str) -> bool:
        return bool(self._redis.exists(key))

    def keys(self, pattern: str) -> list[str]:
        return self._redis.keys(pattern)


def create_session_store() -> SessionStore:
    """Factory: create Redis store if configured, else in-memory fallback."""
    if settings.redis_url:
        try:
            store = RedisSessionStore(settings.redis_url)
            store._redis.ping()
            return store
        except Exception as e:
            logger.warning("redis_unavailable_falling_back_to_memory", error=str(e))
    return InMemorySessionStore()


session_store = create_session_store()
