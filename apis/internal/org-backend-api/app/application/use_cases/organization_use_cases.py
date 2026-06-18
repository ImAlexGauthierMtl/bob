"""Organization application use cases."""
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Protocol

from app.domain.exceptions import OrganizationNotFoundError


OrganizationEntity = Any
OrganizationFactory = Callable[..., OrganizationEntity]
OrganizationPublisher = Callable[[str, dict[str, Any]], Awaitable[None]]
OrganizationDeletedPublisher = Callable[[str], Awaitable[None]]


class OrganizationRepositoryPort(Protocol):
    def create(self, org: OrganizationEntity) -> OrganizationEntity:
        ...

    def get_by_id(self, org_id: str, tenant_id: str) -> Optional[OrganizationEntity]:
        ...

    def list_all(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> list[OrganizationEntity]:
        ...

    def count(self, tenant_id: str) -> int:
        ...

    def update(self, org: OrganizationEntity) -> OrganizationEntity:
        ...

    def soft_delete(
        self,
        org: OrganizationEntity,
        deleted_by: str,
        reason: Optional[str] = None,
    ) -> OrganizationEntity:
        ...


@dataclass(frozen=True)
class OrganizationListResult:
    items: list[OrganizationEntity]
    total: int
    skip: int
    limit: int


class OrganizationUseCases:
    def __init__(
        self,
        repo: OrganizationRepositoryPort,
        create_organization_entity: OrganizationFactory,
        publish_created: OrganizationPublisher,
        publish_updated: OrganizationPublisher,
        publish_deleted: OrganizationDeletedPublisher,
    ) -> None:
        self.repo = repo
        self.create_organization_entity = create_organization_entity
        self.publish_created = publish_created
        self.publish_updated = publish_updated
        self.publish_deleted = publish_deleted

    async def list_organizations(
        self,
        tenant_id: str,
        skip: int,
        limit: int,
        search: Optional[str],
    ) -> OrganizationListResult:
        return OrganizationListResult(
            items=self.repo.list_all(tenant_id, skip, limit, search),
            total=self.repo.count(tenant_id),
            skip=skip,
            limit=limit,
        )

    async def create_organization(
        self,
        data: dict[str, Any],
        user: dict[str, Any],
    ) -> OrganizationEntity:
        org = self.create_organization_entity(
            **data,
            tenant_id=user["tenant_id"],
            owner_id=user["user_id"],
            created_by=user["email"],
        )
        created = self.repo.create(org)
        await self.publish_created(
            created.id,
            {"name": created.name, "tenant_id": created.tenant_id},
        )
        return created

    async def get_organization(self, org_id: str, tenant_id: str) -> OrganizationEntity:
        org = self.repo.get_by_id(org_id, tenant_id)
        if not org:
            raise OrganizationNotFoundError
        return org

    async def update_organization(
        self,
        org_id: str,
        updates: dict[str, Any],
        user: dict[str, Any],
    ) -> OrganizationEntity:
        org = await self.get_organization(org_id, user["tenant_id"])
        for key, value in updates.items():
            setattr(org, key, value)
        org.updated_by = user["email"]
        updated = self.repo.update(org)
        await self.publish_updated(updated.id, {"fields": list(updates.keys())})
        return updated

    async def delete_organization(self, org_id: str, user: dict[str, Any]) -> None:
        org = await self.get_organization(org_id, user["tenant_id"])
        self.repo.soft_delete(org, user["email"])
        await self.publish_deleted(org_id)
