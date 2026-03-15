"""Event Bus publishers for contact~backend-api."""

from shared.event_bus import event_bus, Event


def publish_contact_created(payload: dict):
    event_bus.publish(Event(
        event_type="contact.created",
        payload=payload,
        source="contact~backend-api",
    ))


def publish_contact_updated(payload: dict):
    event_bus.publish(Event(
        event_type="contact.updated",
        payload=payload,
        source="contact~backend-api",
    ))


def publish_contact_deleted(payload: dict):
    event_bus.publish(Event(
        event_type="contact.deleted",
        payload=payload,
        source="contact~backend-api",
    ))
