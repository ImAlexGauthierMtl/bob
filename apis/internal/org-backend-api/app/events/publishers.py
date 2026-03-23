"""Event publishers for organization domain."""
from shared.event_bus import event_bus
from shared.event_bus.schemas import org_created, org_updated, org_deleted
from shared.infrastructure import get_logger

logger = get_logger(__name__)


async def publish_org_created(org_id: str, data: dict) -> None:
    event = org_created(org_id, data)
    await event_bus.publish(event)
    logger.info("published_org_created", org_id=org_id)


async def publish_org_updated(org_id: str, data: dict) -> None:
    event = org_updated(org_id, data)
    await event_bus.publish(event)
    logger.info("published_org_updated", org_id=org_id)


async def publish_org_deleted(org_id: str) -> None:
    event = org_deleted(org_id)
    await event_bus.publish(event)
    logger.info("published_org_deleted", org_id=org_id)
