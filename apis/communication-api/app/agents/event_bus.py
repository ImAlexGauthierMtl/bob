"""Event Bus — placeholder."""


class EventBus:
    """Placeholder for event bus."""
    
    def emit(self, event_name: str, data: dict) -> None:
        """Emit an event."""
        raise NotImplementedError()


event_bus = EventBus()
