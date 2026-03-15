"""Event Bus publishers for usage~backend-api."""

from shared.event_bus import event_bus, Event


def publish_usage_created(payload: dict):
    event_bus.publish(Event(
        event_type="usage.created",
        payload=payload,
        source="usage~backend-api",
    ))


def publish_usage_updated(payload: dict):
    event_bus.publish(Event(
        event_type="usage.updated",
        payload=payload,
        source="usage~backend-api",
    ))


def publish_usage_deleted(payload: dict):
    event_bus.publish(Event(
        event_type="usage.deleted",
        payload=payload,
        source="usage~backend-api",
    ))
