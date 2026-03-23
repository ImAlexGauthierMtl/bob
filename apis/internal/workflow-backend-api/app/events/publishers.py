"""Event publishers for workflow domain."""
from shared.event_bus import event_bus
from shared.infrastructure import get_logger

logger = get_logger(__name__)


async def publish_workflow_created(workflow_id: str, data: dict) -> None:
    await event_bus.publish({"type": "workflow.created", "workflow_id": workflow_id, "data": data})
    logger.info("published_workflow_created", workflow_id=workflow_id)


async def publish_workflow_updated(workflow_id: str, data: dict) -> None:
    await event_bus.publish({"type": "workflow.updated", "workflow_id": workflow_id, "data": data})
    logger.info("published_workflow_updated", workflow_id=workflow_id)


async def publish_workflow_deleted(workflow_id: str) -> None:
    await event_bus.publish({"type": "workflow.deleted", "workflow_id": workflow_id})
    logger.info("published_workflow_deleted", workflow_id=workflow_id)


async def publish_workflow_executed(workflow_id: str, execution_id: str, data: dict) -> None:
    await event_bus.publish({"type": "workflow.executed", "workflow_id": workflow_id, "execution_id": execution_id, "data": data})
    logger.info("published_workflow_executed", workflow_id=workflow_id, execution_id=execution_id)
