"""Event publishers for KB domain."""
from shared.event_bus import event_bus
from shared.infrastructure import get_logger

logger = get_logger(__name__)


async def publish_article_created(article_id: str, data: dict) -> None:
    await event_bus.publish({"type": "kb.article.created", "article_id": article_id, "data": data})
    logger.info("published_article_created", article_id=article_id)


async def publish_article_updated(article_id: str, data: dict) -> None:
    await event_bus.publish({"type": "kb.article.updated", "article_id": article_id, "data": data})
    logger.info("published_article_updated", article_id=article_id)


async def publish_article_deleted(article_id: str) -> None:
    await event_bus.publish({"type": "kb.article.deleted", "article_id": article_id})
    logger.info("published_article_deleted", article_id=article_id)
