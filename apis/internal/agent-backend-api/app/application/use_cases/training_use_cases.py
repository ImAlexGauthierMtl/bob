"""Training application use cases."""
from typing import Any, Callable, Optional, Protocol

from app.domain.exceptions import (
    TrainingMissingElementNotFoundError,
    TrainingNoteNotFoundError,
    TrainingSessionNotFoundError,
)


TrainingEntity = Any
TrainingFactory = Callable[..., TrainingEntity]
IdFactory = Callable[[], str]


class TrainingRepositoryPort(Protocol):
    def create_session(self, session: TrainingEntity) -> TrainingEntity:
        ...

    def get_session(self, session_id: str, user_id: str) -> Optional[TrainingEntity]:
        ...

    def update_session_slide(self, session: TrainingEntity, current_slide: int) -> None:
        ...

    def list_notes(self, session_id: str, user_id: str) -> list[TrainingEntity]:
        ...

    def create_note(self, note: TrainingEntity) -> TrainingEntity:
        ...

    def get_note(self, note_id: str, user_id: str) -> Optional[TrainingEntity]:
        ...

    def delete_note(self, note: TrainingEntity) -> None:
        ...

    def list_missing(self, session_id: str, user_id: str) -> list[TrainingEntity]:
        ...

    def create_missing(self, item: TrainingEntity) -> TrainingEntity:
        ...

    def get_missing(self, item_id: str, user_id: str) -> Optional[TrainingEntity]:
        ...

    def delete_missing(self, item: TrainingEntity) -> None:
        ...


class TrainingUseCases:
    def __init__(
        self,
        repo: TrainingRepositoryPort,
        create_session_entity: TrainingFactory,
        create_note_entity: TrainingFactory,
        create_missing_entity: TrainingFactory,
        create_id: IdFactory,
    ) -> None:
        self.repo = repo
        self.create_session_entity = create_session_entity
        self.create_note_entity = create_note_entity
        self.create_missing_entity = create_missing_entity
        self.create_id = create_id

    async def create_session(self, training_slug: str, user: dict[str, Any]) -> TrainingEntity:
        session = self.create_session_entity(
            id=self.create_id(),
            user_id=user["user_id"],
            tenant_id=user["tenant_id"],
            training_slug=training_slug,
        )
        return self.repo.create_session(session)

    async def update_slide(self, session_id: str, current_slide: int, user: dict[str, Any]) -> dict[str, Any]:
        session = self.repo.get_session(session_id, user["user_id"])
        if not session:
            raise TrainingSessionNotFoundError
        self.repo.update_session_slide(session, current_slide)
        return {"status": "ok", "current_slide": current_slide}

    async def list_notes(self, session_id: str, user: dict[str, Any]) -> list[TrainingEntity]:
        return self.repo.list_notes(session_id, user["user_id"])

    async def create_note(self, session_id: str, data: dict[str, Any], user: dict[str, Any]) -> TrainingEntity:
        note = self.create_note_entity(
            id=self.create_id(),
            session_id=session_id,
            user_id=user["user_id"],
            slide_id=data.get("slide_id"),
            content=data["content"],
            note_type=data["note_type"],
        )
        return self.repo.create_note(note)

    async def delete_note(self, note_id: str, user: dict[str, Any]) -> None:
        note = self.repo.get_note(note_id, user["user_id"])
        if not note:
            raise TrainingNoteNotFoundError
        self.repo.delete_note(note)

    async def list_missing(self, session_id: str, user: dict[str, Any]) -> list[TrainingEntity]:
        return self.repo.list_missing(session_id, user["user_id"])

    async def create_missing(self, session_id: str, data: dict[str, Any], user: dict[str, Any]) -> TrainingEntity:
        item = self.create_missing_entity(
            id=self.create_id(),
            session_id=session_id,
            user_id=user["user_id"],
            label=data["label"],
            category=data["category"],
            description=data.get("description"),
        )
        return self.repo.create_missing(item)

    async def delete_missing(self, item_id: str, user: dict[str, Any]) -> None:
        item = self.repo.get_missing(item_id, user["user_id"])
        if not item:
            raise TrainingMissingElementNotFoundError
        self.repo.delete_missing(item)
