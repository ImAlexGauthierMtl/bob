"""Event Bus with pluggable backends (in-memory for dev, Redis Streams for prod).

Configure via EVENT_BUS_BACKEND env var: 'memory' (default) or 'redis'.
"""

from typing import Callable, Dict, List, Any, Optional, Awaitable, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import asyncio
import json
import os
import uuid

from ..infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Event:
    """Domain event carrying data between services."""

    event_type: str
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            event_id=data.get("event_id", str(uuid.uuid4())),
            event_type=data["event_type"],
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            source=data.get("source", ""),
        )


EventHandler = Callable[[Event], Union[None, Awaitable[None]]]


class EventBusBackend(str, Enum):
    MEMORY = "memory"
    REDIS = "redis"


class InMemoryEventBus:
    """In-memory pub/sub for development and testing."""

    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info("event_subscribed", event_type=event_type, handler=handler.__name__)

    async def publish(self, event: Event) -> None:
        logger.info("event_published", event_type=event.event_type, event_id=event.event_id, source=event.source)
        for handler in self._handlers.get(event.event_type, []):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error("event_handler_error", event_type=event.event_type, error=str(e))

    async def close(self) -> None:
        pass


class RedisEventBus:
    """Redis Streams-backed event bus for production."""

    def __init__(self, redis_url: str, consumer_group: str = "default", consumer_name: Optional[str] = None):
        self._redis_url = redis_url
        self._consumer_group = consumer_group
        self._consumer_name = consumer_name or f"consumer-{uuid.uuid4().hex[:8]}"
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._redis = None
        self._listening = False

    async def _get_redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
            except ImportError:
                raise RuntimeError("redis package required for Redis event bus: pip install redis[hiredis]")
        return self._redis

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info("redis_event_subscribed", event_type=event_type, handler=handler.__name__)

    async def publish(self, event: Event) -> None:
        r = await self._get_redis()
        stream_key = f"events:{event.event_type}"
        data = {"data": json.dumps(event.to_dict())}
        await r.xadd(stream_key, data, maxlen=10000)
        logger.info("redis_event_published", event_type=event.event_type, event_id=event.event_id, stream=stream_key)

    async def start_listening(self) -> None:
        """Start consuming events from Redis Streams in background."""
        if self._listening:
            return
        self._listening = True
        r = await self._get_redis()

        for event_type in self._handlers:
            stream_key = f"events:{event_type}"
            try:
                await r.xgroup_create(stream_key, self._consumer_group, id="0", mkstream=True)
            except Exception:
                pass  # group already exists

        asyncio.create_task(self._consume_loop())

    async def _consume_loop(self) -> None:
        r = await self._get_redis()
        streams = {f"events:{et}": ">" for et in self._handlers}
        if not streams:
            return

        while self._listening:
            try:
                results = await r.xreadgroup(
                    self._consumer_group, self._consumer_name,
                    streams, count=10, block=1000,
                )
                for stream_key, messages in results:
                    event_type = stream_key.split(":", 1)[1] if ":" in stream_key else stream_key
                    for msg_id, msg_data in messages:
                        try:
                            event = Event.from_dict(json.loads(msg_data["data"]))
                            for handler in self._handlers.get(event_type, []):
                                result = handler(event)
                                if asyncio.iscoroutine(result):
                                    await result
                            await r.xack(stream_key, self._consumer_group, msg_id)
                        except Exception as e:
                            logger.error("redis_event_handler_error", stream=stream_key, error=str(e))
            except Exception as e:
                logger.error("redis_consume_error", error=str(e))
                await asyncio.sleep(1)

    async def close(self) -> None:
        self._listening = False
        if self._redis:
            await self._redis.close()
            self._redis = None


def create_event_bus(
    backend: Optional[str] = None,
    redis_url: Optional[str] = None,
    consumer_group: Optional[str] = None,
) -> Union[InMemoryEventBus, RedisEventBus]:
    """Factory to create the appropriate event bus backend.

    Config via env vars:
        EVENT_BUS_BACKEND: 'memory' or 'redis'
        REDIS_URL: redis connection string
        EVENT_BUS_CONSUMER_GROUP: consumer group name
    """
    backend = backend or os.environ.get("EVENT_BUS_BACKEND", "memory")
    if backend == EventBusBackend.REDIS:
        url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        group = consumer_group or os.environ.get("EVENT_BUS_CONSUMER_GROUP", "default")
        return RedisEventBus(redis_url=url, consumer_group=group)
    return InMemoryEventBus()


event_bus = create_event_bus()
