"""Event publishers for opportunity domain."""
from shared.event_bus import event_bus
from shared.event_bus.schemas import opportunity_created, opportunity_updated
from shared.infrastructure import get_logger

logger = get_logger(__name__)


async def publish_opportunity_created(opp_id: str, data: dict) -> None:
    event = opportunity_created(opp_id, data)
    await event_bus.publish(event)
    logger.info("published_opportunity_created", opportunity_id=opp_id)


async def publish_opportunity_updated(opp_id: str, data: dict) -> None:
    event = opportunity_updated(opp_id, data)
    await event_bus.publish(event)
    logger.info("published_opportunity_updated", opportunity_id=opp_id)
