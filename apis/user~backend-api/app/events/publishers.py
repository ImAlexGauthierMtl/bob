"""Event publishers for user domain."""
from shared.event_bus import event_bus
from shared.event_bus.schemas import user_created, user_updated, user_deleted
from shared.infrastructure import get_logger

logger = get_logger(__name__)

async def publish_user_created(user_id: str, data: dict) -> None:
    event = user_created(user_id, data)
    await event_bus.publish(event)
    logger.info("published_user_created", user_id=user_id)

async def publish_user_updated(user_id: str, data: dict) -> None:
    event = user_updated(user_id, data)
    await event_bus.publish(event)

async def publish_user_deleted(user_id: str) -> None:
    event = user_deleted(user_id)
    await event_bus.publish(event)
