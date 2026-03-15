"""Event Bus publishers for agent~backend-api."""

from shared.event_bus import event_bus, Event


def publish_agent_created(payload: dict):
    event_bus.publish(Event(
        event_type="agent.created",
        payload=payload,
        source="agent~backend-api",
    ))


def publish_agent_updated(payload: dict):
    event_bus.publish(Event(
        event_type="agent.updated",
        payload=payload,
        source="agent~backend-api",
    ))


def publish_agent_deleted(payload: dict):
    event_bus.publish(Event(
        event_type="agent.deleted",
        payload=payload,
        source="agent~backend-api",
    ))
