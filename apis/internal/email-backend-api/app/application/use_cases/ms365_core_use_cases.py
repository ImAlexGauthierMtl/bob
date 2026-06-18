"""MS365 storage use cases."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional, Protocol

from app.domain.exceptions import (
    ConnectionAlreadyExistsError,
    ConnectionNotFoundError,
    EmailNotFoundError,
    EventNotFoundError,
)


EmailPublisher = Callable[[str, dict[str, Any]], Awaitable[None]]


class MS365RepositoryPort(Protocol):
    def get_connection_by_user(self, user_id: str, tenant_id: str) -> Optional[Any]:
        ...

    def get_connection_by_id(self, conn_id: str, tenant_id: str) -> Optional[Any]:
        ...

    def get_all_active_connections(self) -> list[Any]:
        ...

    def create_connection(self, data: dict[str, Any], tenant_id: str) -> Any:
        ...

    def update_connection(self, conn: Any, data: dict[str, Any]) -> Any:
        ...

    def soft_delete_connection(self, conn: Any, deleted_by: str) -> Any:
        ...

    def list_emails(self, *args: Any) -> list[Any]:
        ...

    def count_emails(self, *args: Any) -> int:
        ...

    def get_email_by_id(self, email_id: str, user_id: str, tenant_id: str) -> Optional[Any]:
        ...

    def upsert_email(self, data: dict[str, Any], tenant_id: str) -> Any:
        ...

    def update_email(self, email: Any, data: dict[str, Any]) -> Any:
        ...

    def delete_email(self, email: Any) -> None:
        ...

    def list_events(self, *args: Any) -> list[Any]:
        ...

    def count_events(self, *args: Any) -> int:
        ...

    def get_event_by_id(self, event_id: str, user_id: str, tenant_id: str) -> Optional[Any]:
        ...

    def upsert_event(self, data: dict[str, Any], tenant_id: str) -> Any:
        ...

    def update_event(self, event: Any, data: dict[str, Any]) -> Any:
        ...

    def delete_event(self, event: Any) -> None:
        ...

    def get_email_contacts(self, synced_email_id: str) -> list[Any]:
        ...

    def link_email_contact(self, synced_email_id: str, contact_id: str, role: str = "from") -> None:
        ...

    def unlink_email_contact(self, synced_email_id: str, contact_id: str) -> None:
        ...


@dataclass(frozen=True)
class ListResult:
    items: list[Any]
    total: int
    skip: int
    limit: int


class MS365CoreUseCases:
    def __init__(self, repo: MS365RepositoryPort, publish_email_received: EmailPublisher) -> None:
        self.repo = repo
        self.publish_email_received = publish_email_received

    async def get_connection_by_user(self, user_id: str, tenant_id: str) -> Optional[Any]:
        return self.repo.get_connection_by_user(user_id, tenant_id)

    async def get_connection(self, conn_id: str, tenant_id: str) -> Any:
        conn = self.repo.get_connection_by_id(conn_id, tenant_id)
        if not conn:
            raise ConnectionNotFoundError
        return conn

    async def list_active_connections(self) -> list[Any]:
        return self.repo.get_all_active_connections()

    async def create_connection(self, data: dict[str, Any], tenant_id: str) -> Any:
        existing = self.repo.get_connection_by_user(data["user_id"], tenant_id)
        if existing:
            raise ConnectionAlreadyExistsError
        return self.repo.create_connection(data, tenant_id)

    async def update_connection(self, conn_id: str, data: dict[str, Any], tenant_id: str) -> Any:
        conn = await self.get_connection(conn_id, tenant_id)
        return self.repo.update_connection(conn, data)

    async def delete_connection(self, conn_id: str, user: dict[str, Any]) -> None:
        conn = await self.get_connection(conn_id, user["tenant_id"])
        self.repo.soft_delete_connection(conn, user.get("email", "system"))

    async def list_emails(
        self,
        user_id: str,
        tenant_id: str,
        skip: int,
        limit: int,
        folder: Optional[str],
        search: Optional[str],
        linked_contact_id: Optional[str],
        smart_label: Optional[str],
    ) -> ListResult:
        return ListResult(
            items=self.repo.list_emails(user_id, tenant_id, skip, limit, folder, search, linked_contact_id, smart_label),
            total=self.repo.count_emails(user_id, tenant_id, folder, search, linked_contact_id, smart_label),
            skip=skip,
            limit=limit,
        )

    async def get_email(self, email_id: str, user_id: str, tenant_id: str) -> Any:
        email = self.repo.get_email_by_id(email_id, user_id, tenant_id)
        if not email:
            raise EmailNotFoundError
        return email

    async def upsert_email(self, data: dict[str, Any], tenant_id: str) -> Any:
        email = self.repo.upsert_email(data, tenant_id)
        await self.publish_email_received(email.id, {"subject": email.subject, "from": email.from_address})
        return email

    async def update_email(self, email_id: str, user_id: str, tenant_id: str, data: dict[str, Any]) -> Any:
        email = await self.get_email(email_id, user_id, tenant_id)
        return self.repo.update_email(email, data)

    async def delete_email(self, email_id: str, user_id: str, tenant_id: str) -> None:
        email = await self.get_email(email_id, user_id, tenant_id)
        self.repo.delete_email(email)

    async def list_events(
        self,
        user_id: str,
        tenant_id: str,
        skip: int,
        limit: int,
        from_date: Optional[datetime],
        to_date: Optional[datetime],
    ) -> ListResult:
        return ListResult(
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

    async def upsert_event(self, data: dict[str, Any], tenant_id: str) -> Any:
        return self.repo.upsert_event(data, tenant_id)

    async def update_event(self, event_id: str, user_id: str, tenant_id: str, data: dict[str, Any]) -> Any:
        event = await self.get_event(event_id, user_id, tenant_id)
        return self.repo.update_event(event, data)

    async def delete_event(self, event_id: str, user_id: str, tenant_id: str) -> None:
        event = await self.get_event(event_id, user_id, tenant_id)
        self.repo.delete_event(event)

    async def list_email_contacts(self, email_id: str) -> list[Any]:
        return self.repo.get_email_contacts(email_id)

    async def link_email_contact(self, email_id: str, contact_id: str, role: str) -> dict[str, str]:
        self.repo.link_email_contact(email_id, contact_id, role)
        return {"status": "linked"}

    async def unlink_email_contact(self, email_id: str, contact_id: str) -> None:
        self.repo.unlink_email_contact(email_id, contact_id)
