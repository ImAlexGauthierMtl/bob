"""Contact application use cases."""
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Protocol

from app.domain.exceptions import ContactNotFoundError


ContactEntity = Any
ContactFactory = Callable[..., ContactEntity]
ContactPublisher = Callable[[str, dict[str, Any]], Awaitable[None]]
ContactDeletedPublisher = Callable[[str], Awaitable[None]]


class ContactRepositoryPort(Protocol):
    def create(self, contact: ContactEntity) -> ContactEntity:
        ...

    def get_by_id(self, contact_id: str, tenant_id: str) -> Optional[ContactEntity]:
        ...

    def list_all(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> list[ContactEntity]:
        ...

    def count(self, tenant_id: str, organization_id: Optional[str] = None) -> int:
        ...

    def update(self, contact: ContactEntity) -> ContactEntity:
        ...

    def soft_delete(
        self,
        contact: ContactEntity,
        deleted_by: str,
        reason: Optional[str] = None,
    ) -> ContactEntity:
        ...


@dataclass(frozen=True)
class ContactListResult:
    items: list[ContactEntity]
    total: int
    skip: int
    limit: int


class ContactUseCases:
    def __init__(
        self,
        repo: ContactRepositoryPort,
        create_contact_entity: ContactFactory,
        publish_created: ContactPublisher,
        publish_updated: ContactPublisher,
        publish_deleted: ContactDeletedPublisher,
    ) -> None:
        self.repo = repo
        self.create_contact_entity = create_contact_entity
        self.publish_created = publish_created
        self.publish_updated = publish_updated
        self.publish_deleted = publish_deleted

    async def list_contacts(
        self,
        tenant_id: str,
        skip: int,
        limit: int,
        search: Optional[str],
        organization_id: Optional[str],
    ) -> ContactListResult:
        return ContactListResult(
            items=self.repo.list_all(tenant_id, skip, limit, search, organization_id),
            total=self.repo.count(tenant_id, organization_id),
            skip=skip,
            limit=limit,
        )

    async def create_contact(self, data: dict[str, Any], user: dict[str, Any]) -> ContactEntity:
        contact = self.create_contact_entity(
            **data,
            tenant_id=user["tenant_id"],
            owner_id=user["user_id"],
            created_by=user["email"],
        )
        created = self.repo.create(contact)
        await self.publish_created(
            created.id,
            {"email": created.email, "tenant_id": created.tenant_id},
        )
        return created

    async def get_contact(self, contact_id: str, tenant_id: str) -> ContactEntity:
        contact = self.repo.get_by_id(contact_id, tenant_id)
        if not contact:
            raise ContactNotFoundError
        return contact

    async def update_contact(
        self,
        contact_id: str,
        updates: dict[str, Any],
        user: dict[str, Any],
    ) -> ContactEntity:
        contact = await self.get_contact(contact_id, user["tenant_id"])
        for key, value in updates.items():
            setattr(contact, key, value)
        contact.updated_by = user["email"]
        updated = self.repo.update(contact)
        await self.publish_updated(updated.id, {"fields": list(updates.keys())})
        return updated

    async def delete_contact(self, contact_id: str, user: dict[str, Any]) -> None:
        contact = await self.get_contact(contact_id, user["tenant_id"])
        self.repo.soft_delete(contact, user["email"])
        await self.publish_deleted(contact_id)
