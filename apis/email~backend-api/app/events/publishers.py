"""Event publishers for email domain."""
from shared.event_bus import event_bus
from shared.event_bus.schemas import email_received, email_synced
from shared.infrastructure import get_logger

logger = get_logger(__name__)


async def publish_email_received(email_id: str, data: dict) -> None:
    event = email_received(email_id, data)
    await event_bus.publish(event)
    logger.info("published_email_received", email_id=email_id)


async def publish_email_synced(email_id: str, data: dict) -> None:
    event = email_synced(email_id, data)
    await event_bus.publish(event)
    logger.info("published_email_synced", email_id=email_id)
