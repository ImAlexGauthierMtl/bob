"""Workflow event bus placeholder for communication webhooks."""


class WorkflowEventBus:
    """Minimal async interface used by webhook routes."""

    async def publish(self, event_name: str, payload: dict, tenant_id: str, triggered_by: str) -> list[str]:
        return []


event_bus = WorkflowEventBus()
