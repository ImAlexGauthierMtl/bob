"""Event Bus publishers for product~backend-api."""

from shared.event_bus import event_bus, Event


def publish_product_created(payload: dict):
    event_bus.publish(Event(
        event_type="product.created",
        payload=payload,
        source="product~backend-api",
    ))


def publish_product_updated(payload: dict):
    event_bus.publish(Event(
        event_type="product.updated",
        payload=payload,
        source="product~backend-api",
    ))


def publish_product_deleted(payload: dict):
    event_bus.publish(Event(
        event_type="product.deleted",
        payload=payload,
        source="product~backend-api",
    ))
