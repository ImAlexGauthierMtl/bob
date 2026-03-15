"""Event Bus publishers for opportunity~backend-api."""

from shared.event_bus import event_bus, Event


def publish_opportunity_created(payload: dict):
    event_bus.publish(Event(
        event_type="opportunity.created",
        payload=payload,
        source="opportunity~backend-api",
    ))


def publish_opportunity_updated(payload: dict):
    event_bus.publish(Event(
        event_type="opportunity.updated",
        payload=payload,
        source="opportunity~backend-api",
    ))


def publish_opportunity_deleted(payload: dict):
    event_bus.publish(Event(
        event_type="opportunity.deleted",
        payload=payload,
        source="opportunity~backend-api",
    ))
