"""Event publishers for usage domain."""
from shared.event_bus import event_bus
from shared.infrastructure import get_logger

logger = get_logger(__name__)


async def publish_usage_recorded(txn_id: str, data: dict) -> None:
    await event_bus.publish({"type": "usage.recorded", "transaction_id": txn_id, "data": data})
    logger.info("published_usage_recorded", transaction_id=txn_id)
