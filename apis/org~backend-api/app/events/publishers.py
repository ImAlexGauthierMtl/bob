"""Event Bus publishers for org~backend-api."""

from shared.event_bus import event_bus, Event


def publish_org_created(payload: dict):
    event_bus.publish(Event(
        event_type="org.created",
        payload=payload,
        source="org~backend-api",
    ))


def publish_org_updated(payload: dict):
    event_bus.publish(Event(
        event_type="org.updated",
        payload=payload,
        source="org~backend-api",
    ))


def publish_org_deleted(payload: dict):
    event_bus.publish(Event(
        event_type="org.deleted",
        payload=payload,
        source="org~backend-api",
    ))
