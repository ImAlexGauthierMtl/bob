"""Product application use cases."""
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Protocol

from app.domain.exceptions import ProductNotFoundError


ProductEntity = Any
ProductFactory = Callable[..., ProductEntity]
ProductPublisher = Callable[[str, dict[str, Any]], Awaitable[None]]


class ProductRepositoryPort(Protocol):
    def create(self, product: ProductEntity) -> ProductEntity:
        ...

    def get_by_id(self, product_id: str, tenant_id: str) -> Optional[ProductEntity]:
        ...

    def list_all(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
        category: Optional[str] = None,
        active_only: bool = True,
    ) -> list[ProductEntity]:
        ...

    def count(self, tenant_id: str, active_only: bool = True) -> int:
        ...

    def update(self, product: ProductEntity) -> ProductEntity:
        ...

    def soft_delete(self, product: ProductEntity, deleted_by: str) -> ProductEntity:
        ...


@dataclass(frozen=True)
class ProductListResult:
    items: list[ProductEntity]
    total: int
    skip: int
    limit: int


class ProductUseCases:
    def __init__(
        self,
        repo: ProductRepositoryPort,
        create_product_entity: ProductFactory,
        publish_created: ProductPublisher,
        publish_updated: ProductPublisher,
    ) -> None:
        self.repo = repo
        self.create_product_entity = create_product_entity
        self.publish_created = publish_created
        self.publish_updated = publish_updated

    async def list_products(
        self,
        tenant_id: str,
        skip: int,
        limit: int,
        category: Optional[str],
    ) -> ProductListResult:
        return ProductListResult(
            items=self.repo.list_all(tenant_id, skip, limit, category),
            total=self.repo.count(tenant_id),
            skip=skip,
            limit=limit,
        )

    async def create_product(self, data: dict[str, Any], user: dict[str, Any]) -> ProductEntity:
        product = self.create_product_entity(
            **data,
            tenant_id=user["tenant_id"],
            created_by=user["email"],
        )
        created = self.repo.create(product)
        await self.publish_created(
            created.id,
            {"name": created.name, "tenant_id": created.tenant_id},
        )
        return created

    async def get_product(self, product_id: str, tenant_id: str) -> ProductEntity:
        product = self.repo.get_by_id(product_id, tenant_id)
        if not product:
            raise ProductNotFoundError
        return product

    async def update_product(
        self,
        product_id: str,
        updates: dict[str, Any],
        user: dict[str, Any],
    ) -> ProductEntity:
        product = await self.get_product(product_id, user["tenant_id"])
        for key, value in updates.items():
            setattr(product, key, value)
        product.updated_by = user["email"]
        updated = self.repo.update(product)
        await self.publish_updated(updated.id, {"fields": list(updates.keys())})
        return updated

    async def delete_product(self, product_id: str, user: dict[str, Any]) -> None:
        product = await self.get_product(product_id, user["tenant_id"])
        self.repo.soft_delete(product, user["email"])
