"""CRM dashboard composition service."""

import asyncio
from typing import Any


OPEN_OPPORTUNITY_STAGES = ("PROSPECTING", "QUALIFICATION", "PROPOSAL", "NEGOTIATION")


class CRMDashboardService:
    """Compose CRM dashboard data from multiple backend APIs."""

    def __init__(self, contact_client, org_client, opportunity_client, activity_client, product_client):
        self.contact_client = contact_client
        self.org_client = org_client
        self.opportunity_client = opportunity_client
        self.activity_client = activity_client
        self.product_client = product_client

    async def build_summary(self, current_user: dict, forward_headers: Any = None) -> dict:
        opportunity_queries = [
            self.opportunity_client.list(skip=0, limit=5, stage=stage, forward_headers=forward_headers)
            for stage in OPEN_OPPORTUNITY_STAGES
        ]
        results = await asyncio.gather(
            self.contact_client.list(skip=0, limit=5, forward_headers=forward_headers),
            self.org_client.list(skip=0, limit=5, forward_headers=forward_headers),
            *opportunity_queries,
            self.activity_client.list(skip=0, limit=5, status="PENDING", forward_headers=forward_headers),
            self.product_client.list(skip=0, limit=5, forward_headers=forward_headers),
        )
        contacts = results[0]
        organizations = results[1]
        opportunities = self._merge_payloads(results[2:2 + len(OPEN_OPPORTUNITY_STAGES)], item_limit=5)
        activities = results[-2]
        products = results[-1]

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

    def _merge_payloads(self, payloads: list[Any], item_limit: int) -> dict:
        items = []
        total = 0
        for payload in payloads:
            total += self._total(payload)
            if len(items) < item_limit:
                items.extend(self._items(payload)[:item_limit - len(items)])
        return {"items": items, "total": total, "skip": 0, "limit": item_limit}

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
