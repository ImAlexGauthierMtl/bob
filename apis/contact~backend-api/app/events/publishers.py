"""Event publishers for contact domain."""
from shared.event_bus import event_bus
from shared.event_bus.schemas import contact_created, contact_updated, contact_deleted
from shared.infrastructure import get_logger

logger = get_logger(__name__)


async def publish_contact_created(contact_id: str, data: dict) -> None:
    event = contact_created(contact_id, data)
    await event_bus.publish(event)
    logger.info("published_contact_created", contact_id=contact_id)


async def publish_contact_updated(contact_id: str, data: dict) -> None:
    event = contact_updated(contact_id, data)
    await event_bus.publish(event)
    logger.info("published_contact_updated", contact_id=contact_id)


async def publish_contact_deleted(contact_id: str) -> None:
    event = contact_deleted(contact_id)
    await event_bus.publish(event)
    logger.info("published_contact_deleted", contact_id=contact_id)
