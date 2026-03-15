"""Event Bus publishers for workflow~backend-api."""

from shared.event_bus import event_bus, Event


def publish_workflow_created(payload: dict):
    event_bus.publish(Event(
        event_type="workflow.created",
        payload=payload,
        source="workflow~backend-api",
    ))


def publish_workflow_updated(payload: dict):
    event_bus.publish(Event(
        event_type="workflow.updated",
        payload=payload,
        source="workflow~backend-api",
    ))


def publish_workflow_deleted(payload: dict):
    event_bus.publish(Event(
        event_type="workflow.deleted",
        payload=payload,
        source="workflow~backend-api",
    ))
