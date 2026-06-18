"""Platform overview composition service."""

import asyncio
from typing import Any


class PlatformOverviewService:
    """Compose workflow and usage state for the platform UI."""

    def __init__(self, workflow_client, usage_client):
        self.workflow_client = workflow_client
        self.usage_client = usage_client

    async def build_overview(self, current_user: dict, forward_headers: Any = None) -> dict:
        workflows, monitoring, recent_executions, usage_summary = await asyncio.gather(
            self.workflow_client.list(skip=0, limit=5, forward_headers=forward_headers),
            self.workflow_client.get_monitoring_stats(forward_headers=forward_headers),
            self.workflow_client.get_recent_executions(limit=5, forward_headers=forward_headers),
            self.usage_client.get_summary(forward_headers=forward_headers),
        )

        workflow_items = self._items(workflows)
        execution_items = self._items(recent_executions)
        return {
            "user_id": current_user.get("user_id"),
            "tenant_id": current_user.get("tenant_id"),
            "workflows": workflow_items,
            "recent_executions": execution_items,
            "monitoring": monitoring if isinstance(monitoring, dict) else {},
            "usage": usage_summary if isinstance(usage_summary, dict) else {},
            "totals": {
                "workflows": self._total(workflows),
                "recent_executions": len(execution_items),
            },
        }

    @staticmethod
    def _items(payload: Any) -> list:
        if isinstance(payload, dict):
            items = payload.get("items", [])
            return items if isinstance(items, list) else []
        return payload if isinstance(payload, list) else []

    def _total(self, payload: Any) -> int:
        if isinstance(payload, dict) and isinstance(payload.get("total"), int):
            return payload["total"]
        return len(self._items(payload))
