"""Client Map application use cases."""
from typing import Any, Protocol

from app.domain.exceptions import ClientMapNotFoundError, ContactNotFoundError, GoldenNoteNotFoundError


class ClientMapRepositoryPort(Protocol):
    def contact_exists(self, contact_id: str, tenant_id: str) -> bool:
        ...

    def get_by_contact_id(self, contact_id: str, tenant_id: str) -> Any:
        ...

    def upsert(self, contact_id: str, tenant_id: str, data: dict[str, Any], user_email: str = "") -> Any:
        ...

    def add_golden_note(
        self,
        client_map_id: str,
        tenant_id: str,
        data: dict[str, Any],
        user_email: str = "",
    ) -> Any:
        ...

    def update_golden_note(self, note_id: str, tenant_id: str, data: dict[str, Any]) -> Any:
        ...

    def delete_golden_note(self, note_id: str, tenant_id: str) -> bool:
        ...

    def get_meddpicc_detail(self, contact_id: str, tenant_id: str) -> Any:
        ...


class ClientMapUseCases:
    def __init__(self, repo: ClientMapRepositoryPort) -> None:
        self.repo = repo

    def _verify_contact(self, contact_id: str, tenant_id: str) -> None:
        if not self.repo.contact_exists(contact_id, tenant_id):
            raise ContactNotFoundError

    async def get_client_map(self, contact_id: str, user: dict[str, Any]) -> Any:
        self._verify_contact(contact_id, user["tenant_id"])
        client_map = self.repo.get_by_contact_id(contact_id, user["tenant_id"])
        if not client_map:
            raise ClientMapNotFoundError
        return client_map

    async def upsert_client_map(self, contact_id: str, data: dict[str, Any], user: dict[str, Any]) -> Any:
        self._verify_contact(contact_id, user["tenant_id"])
        return self.repo.upsert(
            contact_id=contact_id,
            tenant_id=user["tenant_id"],
            data=data,
            user_email=user["email"] or "",
        )

    async def create_golden_note(self, contact_id: str, data: dict[str, Any], user: dict[str, Any]) -> Any:
        self._verify_contact(contact_id, user["tenant_id"])
        client_map = self.repo.get_by_contact_id(contact_id, user["tenant_id"])
        if not client_map:
            client_map = self.repo.upsert(
                contact_id=contact_id,
                tenant_id=user["tenant_id"],
                data={},
                user_email=user["email"] or "",
            )
        return self.repo.add_golden_note(
            client_map_id=client_map.id,
            tenant_id=user["tenant_id"],
            data=data,
            user_email=user["email"] or "",
        )

    async def update_golden_note(
        self,
        contact_id: str,
        note_id: str,
        data: dict[str, Any],
        user: dict[str, Any],
    ) -> Any:
        self._verify_contact(contact_id, user["tenant_id"])
        note = self.repo.update_golden_note(note_id, user["tenant_id"], data)
        if not note:
            raise GoldenNoteNotFoundError
        return note

    async def delete_golden_note(self, contact_id: str, note_id: str, user: dict[str, Any]) -> None:
        self._verify_contact(contact_id, user["tenant_id"])
        if not self.repo.delete_golden_note(note_id, user["tenant_id"]):
            raise GoldenNoteNotFoundError

    async def get_meddpicc_score(self, contact_id: str, user: dict[str, Any]) -> Any:
        self._verify_contact(contact_id, user["tenant_id"])
        detail = self.repo.get_meddpicc_detail(contact_id, user["tenant_id"])
        if not detail:
            raise ClientMapNotFoundError
        return detail
