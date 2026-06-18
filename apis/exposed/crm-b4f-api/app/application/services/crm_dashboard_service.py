"""CRM dashboard composition service."""

import asyncio
from typing import Any


class CRMDashboardService:
    """Compose CRM dashboard data from multiple backend APIs."""

    def __init__(self, contact_client, org_client, opportunity_client, activity_client, product_client):
        self.contact_client = contact_client
        self.org_client = org_client
        self.opportunity_client = opportunity_client
        self.activity_client = activity_client
        self.product_client = product_client

    async def build_summary(self, current_user: dict, forward_headers: Any = None) -> dict:
        contacts, organizations, opportunities, activities, products = await asyncio.gather(
            self.contact_client.list(skip=0, limit=5, forward_headers=forward_headers),
            self.org_client.list(skip=0, limit=5, forward_headers=forward_headers),
            self.opportunity_client.list(skip=0, limit=5, stage="OPEN", forward_headers=forward_headers),
            self.activity_client.list(skip=0, limit=5, status="PENDING", forward_headers=forward_headers),
            self.product_client.list(skip=0, limit=5, forward_headers=forward_headers),
        )

        return {
            "user_id": current_user.get("user_id"),
            "tenant_id": current_user.get("tenant_id"),
            "totals": {
                "contacts": self._total(contacts),
                "organizations": self._total(organizations),
                "open_opportunities": self._total(opportunities),
                "pending_activities": self._total(activities),
                "products": self._total(products),
            },
            "highlights": {
                "contacts": self._items(contacts),
                "organizations": self._items(organizations),
                "open_opportunities": self._items(opportunities),
                "pending_activities": self._items(activities),
                "products": self._items(products),
            },
            "next_actions": self._next_actions(opportunities, activities),
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

    def _next_actions(self, opportunities: Any, activities: Any) -> list[dict]:
        actions = []
        if self._total(opportunities):
            actions.append({
                "type": "review_pipeline",
                "label": "Review open opportunities",
                "count": self._total(opportunities),
            })
        if self._total(activities):
            actions.append({
                "type": "follow_up",
                "label": "Complete pending activities",
                "count": self._total(activities),
            })
        return actions
