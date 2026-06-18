"""Membrane CRUD use cases."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Protocol

from app.domain.exceptions import ConnectionNotFoundError, EmailNotFoundError, EventNotFoundError


class MembraneRepositoryPort(Protocol):
    def create_connection(self, data: dict[str, Any], tenant_id: str) -> Any:
        ...

    def get_connection_by_user_integration(self, user_id: str, integration_key: str, tenant_id: str) -> Optional[Any]:
        ...

    def get_first_connection_by_user(self, user_id: str, tenant_id: str) -> Optional[Any]:
        ...

    def get_connection_by_id(self, connection_id: str, tenant_id: str) -> Optional[Any]:
        ...

    def update_connection(self, conn: Any, data: dict[str, Any]) -> Any:
        ...

    def soft_delete_connection(self, conn: Any, deleted_by: str) -> Any:
        ...

    def upsert_email(self, data: dict[str, Any], tenant_id: str) -> Any:
        ...

    def list_emails(self, *args: Any) -> list[Any]:
        ...

    def count_emails(self, *args: Any) -> int:
        ...

    def get_email_by_id(self, email_id: str, user_id: str, tenant_id: str) -> Optional[Any]:
        ...

    def upsert_event(self, data: dict[str, Any], tenant_id: str) -> Any:
        ...

    def list_events(self, *args: Any) -> list[Any]:
        ...

    def count_events(self, *args: Any) -> int:
        ...

    def get_event_by_id(self, event_id: str, user_id: str, tenant_id: str) -> Optional[Any]:
        ...


@dataclass(frozen=True)
class MembraneListResult:
    items: list[Any]
    total: int
    skip: int
    limit: int


class MembraneCrudUseCases:
    def __init__(self, repo: MembraneRepositoryPort) -> None:
        self.repo = repo

    async def create_connection(self, data: dict[str, Any], tenant_id: str) -> Any:
        existing = self.repo.get_connection_by_user_integration(data["user_id"], data["integration_key"], tenant_id)
        if existing:
            return self.repo.update_connection(existing, data)
        return self.repo.create_connection(data, tenant_id)

    async def get_connection_by_user(
        self,
        user_id: str,
        integration_key: Optional[str],
        tenant_id: str,
    ) -> Any:
        if integration_key:
            conn = self.repo.get_connection_by_user_integration(user_id, integration_key, tenant_id)
        else:
            conn = self.repo.get_first_connection_by_user(user_id, tenant_id)
        if not conn:
            raise ConnectionNotFoundError
        return conn

    async def get_connection(self, connection_id: str, tenant_id: str) -> Any:
        conn = self.repo.get_connection_by_id(connection_id, tenant_id)
        if not conn:
            raise ConnectionNotFoundError
        return conn

    async def update_connection(self, connection_id: str, data: dict[str, Any], tenant_id: str) -> Any:
        conn = await self.get_connection(connection_id, tenant_id)
        return self.repo.update_connection(conn, data)

    async def delete_connection(self, connection_id: str, user: dict[str, Any]) -> None:
        conn = await self.get_connection(connection_id, user["tenant_id"])
        self.repo.soft_delete_connection(conn, user.get("user_id", "system"))

    async def upsert_email(self, data: dict[str, Any], tenant_id: str) -> Any:
        return self.repo.upsert_email(data, tenant_id)

    async def list_emails(
        self,
        user_id: str,
        tenant_id: str,
        skip: int,
        limit: int,
        folder: Optional[str],
        search: Optional[str],
    ) -> MembraneListResult:
        return MembraneListResult(
            items=self.repo.list_emails(user_id, tenant_id, skip, limit, folder, search),
            total=self.repo.count_emails(user_id, tenant_id, folder, search),
            skip=skip,
            limit=limit,
        )

    async def get_email(self, email_id: str, user_id: str, tenant_id: str) -> Any:
        email = self.repo.get_email_by_id(email_id, user_id, tenant_id)
        if not email:
            raise EmailNotFoundError
        return email

    async def upsert_event(self, data: dict[str, Any], tenant_id: str) -> Any:
        return self.repo.upsert_event(data, tenant_id)

    async def list_events(
        self,
        user_id: str,
        tenant_id: str,
        skip: int,
        limit: int,
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> MembraneListResult:
        return MembraneListResult(
            items=self.repo.list_events(user_id, tenant_id, skip, limit, from_date, to_date),
            total=self.repo.count_events(user_id, tenant_id, from_date, to_date),
            skip=skip,
            limit=limit,
        )

    async def get_event(self, event_id: str, user_id: str, tenant_id: str) -> Any:
        event = self.repo.get_event_by_id(event_id, user_id, tenant_id)
        if not event:
            raise EventNotFoundError
        return event
