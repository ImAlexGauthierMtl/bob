"""Activity application use cases."""
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Protocol

from app.domain.exceptions import ActivityNotFoundError


ActivityEntity = Any
ActivityFactory = Callable[..., ActivityEntity]
ActivityPublisher = Callable[[str, dict[str, Any]], Awaitable[None]]


class ActivityRepositoryPort(Protocol):
    def create(self, activity: ActivityEntity) -> ActivityEntity:
        ...

    def get_by_id(self, activity_id: str, tenant_id: str) -> Optional[ActivityEntity]:
        ...

    def list_all(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
    ) -> list[ActivityEntity]:
        ...

    def count(self, tenant_id: str, status: Optional[str] = None) -> int:
        ...

    def update(self, activity: ActivityEntity) -> ActivityEntity:
        ...

    def soft_delete(
        self,
        activity: ActivityEntity,
        deleted_by: str,
        reason: Optional[str] = None,
    ) -> ActivityEntity:
        ...


@dataclass(frozen=True)
class ActivityListResult:
    items: list[ActivityEntity]
    total: int
    skip: int
    limit: int


class ActivityUseCases:
    def __init__(
        self,
        repo: ActivityRepositoryPort,
        create_activity_entity: ActivityFactory,
        publish_created: ActivityPublisher,
        publish_updated: ActivityPublisher,
    ) -> None:
        self.repo = repo
        self.create_activity_entity = create_activity_entity
        self.publish_created = publish_created
        self.publish_updated = publish_updated

    async def list_activities(
        self,
        tenant_id: str,
        skip: int,
        limit: int,
        status_filter: Optional[str],
    ) -> ActivityListResult:
        return ActivityListResult(
            items=self.repo.list_all(tenant_id, skip, limit, status_filter),
            total=self.repo.count(tenant_id, status_filter),
            skip=skip,
            limit=limit,
        )

    async def create_activity(self, data: dict[str, Any], user: dict[str, Any]) -> ActivityEntity:
        activity = self.create_activity_entity(
            subject=data["subject"],
            description=data.get("description"),
            activity_type=data.get("activity_type"),
            priority=data.get("priority"),
            status=data.get("status"),
            due_date=data.get("due_date"),
            organization_ids=data.get("organization_ids") or [],
            contact_ids=data.get("contact_ids") or [],
            opportunity_ids=data.get("opportunity_ids") or [],
            assigned_to=data.get("assigned_to"),
            owner_id=data.get("owner_id") or user["user_id"],
            tenant_id=user["tenant_id"],
            created_by=user["email"],
        )
        created = self.repo.create(activity)
        await self.publish_created(
            created.id,
            {"subject": created.subject, "tenant_id": created.tenant_id},
        )
        return created

    async def get_activity(self, activity_id: str, tenant_id: str) -> ActivityEntity:
        activity = self.repo.get_by_id(activity_id, tenant_id)
        if not activity:
            raise ActivityNotFoundError
        return activity

    async def update_activity(
        self,
        activity_id: str,
        updates: dict[str, Any],
        user: dict[str, Any],
    ) -> ActivityEntity:
        activity = await self.get_activity(activity_id, user["tenant_id"])
        for key, value in updates.items():
            setattr(activity, key, value)
        activity.updated_by = user["email"]
        updated = self.repo.update(activity)
        await self.publish_updated(updated.id, {"fields": list(updates.keys())})
        return updated

    async def delete_activity(self, activity_id: str, user: dict[str, Any]) -> None:
        activity = await self.get_activity(activity_id, user["tenant_id"])
        self.repo.soft_delete(activity, user["email"])
