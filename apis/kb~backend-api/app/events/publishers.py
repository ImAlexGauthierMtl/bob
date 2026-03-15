"""Event Bus publishers for kb~backend-api."""

from shared.event_bus import event_bus, Event


def publish_kb_created(payload: dict):
    event_bus.publish(Event(
        event_type="kb.created",
        payload=payload,
        source="kb~backend-api",
    ))


def publish_kb_updated(payload: dict):
    event_bus.publish(Event(
        event_type="kb.updated",
        payload=payload,
        source="kb~backend-api",
    ))


def publish_kb_deleted(payload: dict):
    event_bus.publish(Event(
        event_type="kb.deleted",
        payload=payload,
        source="kb~backend-api",
    ))
