"""Event publishers for agent domain."""
from shared.event_bus import event_bus
from shared.infrastructure import get_logger

logger = get_logger(__name__)


async def publish_agent_event(event_type: str, entity_id: str, data: dict) -> None:
    """Publish a generic agent domain event."""
    event = {
        "type": f"agent.{event_type}",
        "entity_id": entity_id,
        "data": data,
    }
    await event_bus.publish(event)
    logger.info("published_agent_event", event_type=event_type, entity_id=entity_id)
