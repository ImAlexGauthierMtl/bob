"""Event publishers for product domain."""
from shared.event_bus import event_bus
from shared.event_bus.schemas import product_created, product_updated
from shared.infrastructure import get_logger

logger = get_logger(__name__)


async def publish_product_created(product_id: str, data: dict) -> None:
    event = product_created(product_id, data)
    await event_bus.publish(event)
    logger.info("published_product_created", product_id=product_id)


async def publish_product_updated(product_id: str, data: dict) -> None:
    event = product_updated(product_id, data)
    await event_bus.publish(event)
    logger.info("published_product_updated", product_id=product_id)
