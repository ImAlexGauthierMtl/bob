# Template: Event Bus inter-services

> Bus d'événements pub/sub pour communication asynchrone.

## Fichier à créer

`shared/event_bus/event_bus.py`

```python
"""Simple in-memory event bus (use RabbitMQ/Redis Streams in production)."""

from typing import Callable, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid
from ..infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Event:
    """Base event class."""
    event_type: str
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = ""


EventHandler = Callable[[Event], None]


class EventBus:
    """Simple publish/subscribe event bus."""

    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info("event_subscribed", event_type=event_type, handler=handler.__name__)

    def publish(self, event: Event) -> None:
        logger.info("event_published", event_type=event.event_type, event_id=event.event_id)
        for handler in self._handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error("event_handler_error", event_type=event.event_type, error=str(e))

    async def publish_async(self, event: Event) -> None:
        """Async version for use in FastAPI."""
        self.publish(event)


# Singleton
event_bus = EventBus()
```

## Utilisation

```python
from shared.event_bus.event_bus import event_bus, Event

# Publisher
event_bus.publish(Event(
    event_type="client.created",
    payload={"client_id": "123", "name": "ACME"},
    source="clients-backend-api"
))

# Subscriber
def on_client_created(event: Event):
    print(f"New client: {event.payload['name']}")

event_bus.subscribe("client.created", on_client_created)
```
