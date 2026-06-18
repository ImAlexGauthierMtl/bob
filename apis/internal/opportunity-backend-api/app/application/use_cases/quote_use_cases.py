"""Quote application use cases."""
from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol

from app.domain.exceptions import QuoteNotFoundError


QuoteEntity = Any
QuoteFactory = Callable[..., QuoteEntity]


class QuoteRepositoryPort(Protocol):
    def create(self, quote: QuoteEntity) -> QuoteEntity:
        ...

    def get_by_id(self, quote_id: str, tenant_id: str) -> Optional[QuoteEntity]:
        ...

    def list_all(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
        opportunity_id: Optional[str] = None,
    ) -> list[QuoteEntity]:
        ...

    def count(self, tenant_id: str) -> int:
        ...

    def update(self, quote: QuoteEntity) -> QuoteEntity:
        ...

    def soft_delete(
        self,
        quote: QuoteEntity,
        deleted_by: str,
        reason: Optional[str] = None,
    ) -> QuoteEntity:
        ...


@dataclass(frozen=True)
class QuoteListResult:
    items: list[QuoteEntity]
    total: int
    skip: int
    limit: int


class QuoteUseCases:
    def __init__(
        self,
        repo: QuoteRepositoryPort,
        create_quote_entity: QuoteFactory,
    ) -> None:
        self.repo = repo
        self.create_quote_entity = create_quote_entity

    async def list_quotes(
        self,
        tenant_id: str,
        skip: int,
        limit: int,
        opportunity_id: Optional[str],
    ) -> QuoteListResult:
        return QuoteListResult(
            items=self.repo.list_all(tenant_id, skip, limit, opportunity_id),
            total=self.repo.count(tenant_id),
            skip=skip,
            limit=limit,
        )

    async def create_quote(self, data: dict[str, Any], user: dict[str, Any]) -> QuoteEntity:
        quote = self.create_quote_entity(
            **data,
            tenant_id=user["tenant_id"],
            owner_id=user["user_id"],
            created_by=user["email"],
        )
        return self.repo.create(quote)

    async def get_quote(self, quote_id: str, tenant_id: str) -> QuoteEntity:
        quote = self.repo.get_by_id(quote_id, tenant_id)
        if not quote:
            raise QuoteNotFoundError
        return quote

    async def update_quote(
        self,
        quote_id: str,
        updates: dict[str, Any],
        user: dict[str, Any],
    ) -> QuoteEntity:
        quote = await self.get_quote(quote_id, user["tenant_id"])
        for key, value in updates.items():
            setattr(quote, key, value)
        quote.updated_by = user["email"]
        return self.repo.update(quote)

    async def delete_quote(self, quote_id: str, user: dict[str, Any]) -> None:
        quote = await self.get_quote(quote_id, user["tenant_id"])
        self.repo.soft_delete(quote, user["email"])
