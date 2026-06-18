"""Opportunity application use cases."""
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Protocol

from app.domain.exceptions import OpportunityLineItemNotFoundError, OpportunityNotFoundError


OpportunityEntity = Any
OpportunityLineEntity = Any
OpportunityFactory = Callable[..., OpportunityEntity]
OpportunityLineFactory = Callable[..., OpportunityLineEntity]
OpportunityPublisher = Callable[[str, dict[str, Any]], Awaitable[None]]


class OpportunityRepositoryPort(Protocol):
    def create(self, opp: OpportunityEntity) -> OpportunityEntity:
        ...

    def get_by_id(self, opp_id: str, tenant_id: str) -> Optional[OpportunityEntity]:
        ...

    def list_all(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
        organization_id: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> list[OpportunityEntity]:
        ...

    def count(self, tenant_id: str, organization_id: Optional[str] = None) -> int:
        ...

    def update(self, opp: OpportunityEntity) -> OpportunityEntity:
        ...

    def soft_delete(
        self,
        opp: OpportunityEntity,
        deleted_by: str,
        reason: Optional[str] = None,
    ) -> OpportunityEntity:
        ...

    def add_product(self, line_item: OpportunityLineEntity) -> OpportunityLineEntity:
        ...

    def list_products(self, opp_id: str, tenant_id: str) -> list[OpportunityLineEntity]:
        ...

    def get_product_line(
        self,
        line_id: str,
        tenant_id: str,
    ) -> Optional[OpportunityLineEntity]:
        ...

    def remove_product(self, line_item: OpportunityLineEntity) -> None:
        ...


@dataclass(frozen=True)
class OpportunityListResult:
    items: list[OpportunityEntity]
    total: int
    skip: int
    limit: int


class OpportunityUseCases:
    def __init__(
        self,
        repo: OpportunityRepositoryPort,
        create_opportunity_entity: OpportunityFactory,
        create_line_entity: OpportunityLineFactory,
        publish_created: OpportunityPublisher,
        publish_updated: OpportunityPublisher,
    ) -> None:
        self.repo = repo
        self.create_opportunity_entity = create_opportunity_entity
        self.create_line_entity = create_line_entity
        self.publish_created = publish_created
        self.publish_updated = publish_updated

    async def list_opportunities(
        self,
        tenant_id: str,
        skip: int,
        limit: int,
        organization_id: Optional[str],
        stage: Optional[str],
    ) -> OpportunityListResult:
        return OpportunityListResult(
            items=self.repo.list_all(tenant_id, skip, limit, organization_id, stage),
            total=self.repo.count(tenant_id, organization_id),
            skip=skip,
            limit=limit,
        )

    async def create_opportunity(
        self,
        data: dict[str, Any],
        user: dict[str, Any],
    ) -> OpportunityEntity:
        opp = self.create_opportunity_entity(
            **data,
            tenant_id=user["tenant_id"],
            owner_id=user["user_id"],
            created_by=user["email"],
        )
        created = self.repo.create(opp)
        await self.publish_created(
            created.id,
            {"name": created.name, "tenant_id": created.tenant_id},
        )
        return created

    async def get_opportunity(self, opp_id: str, tenant_id: str) -> OpportunityEntity:
        opp = self.repo.get_by_id(opp_id, tenant_id)
        if not opp:
            raise OpportunityNotFoundError
        return opp

    async def update_opportunity(
        self,
        opp_id: str,
        updates: dict[str, Any],
        user: dict[str, Any],
    ) -> OpportunityEntity:
        opp = await self.get_opportunity(opp_id, user["tenant_id"])
        for key, value in updates.items():
            setattr(opp, key, value)
        opp.updated_by = user["email"]
        updated = self.repo.update(opp)
        await self.publish_updated(updated.id, {"fields": list(updates.keys())})
        return updated

    async def delete_opportunity(self, opp_id: str, user: dict[str, Any]) -> None:
        opp = await self.get_opportunity(opp_id, user["tenant_id"])
        self.repo.soft_delete(opp, user["email"])

    async def list_products(self, opp_id: str, tenant_id: str) -> list[OpportunityLineEntity]:
        return self.repo.list_products(opp_id, tenant_id)

    async def add_product(
        self,
        opp_id: str,
        data: dict[str, Any],
        user: dict[str, Any],
    ) -> OpportunityLineEntity:
        await self.get_opportunity(opp_id, user["tenant_id"])
        line = self.create_line_entity(
            opportunity_id=opp_id,
            tenant_id=user["tenant_id"],
            **data,
        )
        return self.repo.add_product(line)

    async def remove_product(
        self,
        line_id: str,
        tenant_id: str,
    ) -> None:
        line = self.repo.get_product_line(line_id, tenant_id)
        if not line:
            raise OpportunityLineItemNotFoundError
        self.repo.remove_product(line)
