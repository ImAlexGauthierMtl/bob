"""Tenant application use cases."""
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from app.domain.exceptions import TenantNotFoundError, TenantSlugAlreadyExistsError


TenantEntity = Any


class TenantRepositoryPort(Protocol):
    def create(self, **kwargs: Any) -> TenantEntity:
        ...

    def get_by_id(self, tenant_id: str) -> Optional[TenantEntity]:
        ...

    def get_by_slug(self, slug: str) -> Optional[TenantEntity]:
        ...

    def get_all(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[TenantEntity], int]:
        ...

    def update(self, tenant: TenantEntity, **kwargs: Any) -> TenantEntity:
        ...

    def soft_delete(self, tenant: TenantEntity) -> None:
        ...


@dataclass(frozen=True)
class TenantListResult:
    items: list[TenantEntity]
    total: int


class TenantUseCases:
    def __init__(self, repo: TenantRepositoryPort) -> None:
        self.repo = repo

    async def list_tenants(
        self,
        search: Optional[str],
        status: Optional[str],
        skip: int,
        limit: int,
    ) -> TenantListResult:
        items, total = self.repo.get_all(search=search, status=status, skip=skip, limit=limit)
        return TenantListResult(items=items, total=total)

    async def get_tenant(self, tenant_id: str) -> TenantEntity:
        tenant = self.repo.get_by_id(tenant_id)
        if not tenant:
            raise TenantNotFoundError
        return tenant

    async def get_tenant_by_slug(self, slug: str) -> TenantEntity:
        tenant = self.repo.get_by_slug(slug)
        if not tenant:
            raise TenantNotFoundError
        return tenant

    async def create_tenant(self, data: dict[str, Any]) -> TenantEntity:
        existing = self.repo.get_by_slug(data["slug"])
        if existing:
            raise TenantSlugAlreadyExistsError
        return self.repo.create(**data)

    async def update_tenant(self, tenant_id: str, updates: dict[str, Any]) -> TenantEntity:
        tenant = await self.get_tenant(tenant_id)
        new_slug = updates.get("slug")
        if new_slug and new_slug != tenant.slug:
            existing = self.repo.get_by_slug(new_slug)
            if existing:
                raise TenantSlugAlreadyExistsError
        return self.repo.update(tenant, **updates)

    async def delete_tenant(self, tenant_id: str) -> None:
        tenant = await self.get_tenant(tenant_id)
        self.repo.soft_delete(tenant)
