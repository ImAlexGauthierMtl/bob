"""Event publishers for activity domain."""
from shared.event_bus import event_bus
from shared.event_bus.schemas import activity_created, activity_updated
from shared.infrastructure import get_logger

logger = get_logger(__name__)


async def publish_activity_created(activity_id: str, data: dict) -> None:
    event = activity_created(activity_id, data)
    await event_bus.publish(event)
    logger.info("published_activity_created", activity_id=activity_id)


async def publish_activity_updated(activity_id: str, data: dict) -> None:
    event = activity_updated(activity_id, data)
    await event_bus.publish(event)
    logger.info("published_activity_updated", activity_id=activity_id)
