"""Event Bus publishers for activity~backend-api."""

from shared.event_bus import event_bus, Event


def publish_activity_created(payload: dict):
    event_bus.publish(Event(
        event_type="activity.created",
        payload=payload,
        source="activity~backend-api",
    ))


def publish_activity_updated(payload: dict):
    event_bus.publish(Event(
        event_type="activity.updated",
        payload=payload,
        source="activity~backend-api",
    ))


def publish_activity_deleted(payload: dict):
    event_bus.publish(Event(
        event_type="activity.deleted",
        payload=payload,
        source="activity~backend-api",
    ))
