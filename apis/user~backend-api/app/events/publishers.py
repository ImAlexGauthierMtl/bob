"""Event Bus publishers for user~backend-api."""

from shared.event_bus import event_bus, Event


def publish_user_created(payload: dict):
    event_bus.publish(Event(
        event_type="user.created",
        payload=payload,
        source="user~backend-api",
    ))


def publish_user_updated(payload: dict):
    event_bus.publish(Event(
        event_type="user.updated",
        payload=payload,
        source="user~backend-api",
    ))


def publish_user_deleted(payload: dict):
    event_bus.publish(Event(
        event_type="user.deleted",
        payload=payload,
        source="user~backend-api",
    ))
