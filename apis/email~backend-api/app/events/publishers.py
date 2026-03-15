"""Event Bus publishers for email~backend-api."""

from shared.event_bus import event_bus, Event


def publish_email_created(payload: dict):
    event_bus.publish(Event(
        event_type="email.created",
        payload=payload,
        source="email~backend-api",
    ))


def publish_email_updated(payload: dict):
    event_bus.publish(Event(
        event_type="email.updated",
        payload=payload,
        source="email~backend-api",
    ))


def publish_email_deleted(payload: dict):
    event_bus.publish(Event(
        event_type="email.deleted",
        payload=payload,
        source="email~backend-api",
    ))
