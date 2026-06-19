"""Conversation application use cases."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Protocol
from uuid import uuid4

from app.domain import (
    ConversationError,
    ConversationMessage,
    ConversationNotFoundError,
    ConversationSession,
    InternalContext,
)


ALLOWED_MESSAGE_ROLES = {"user", "assistant", "system"}


class ConversationRepositoryPort(Protocol):
    def create_session(
        self,
        *,
        session: ConversationSession,
    ) -> ConversationSession:
        ...

    def list_sessions(
        self,
        *,
        tenant_id: str,
        user_id: str,
    ) -> list[ConversationSession]:
        ...

    def get_session(
        self,
        *,
        session_id: str,
        tenant_id: str,
        user_id: str,
    ) -> Optional[ConversationSession]:
        ...

    def delete_session(
        self,
        *,
        session_id: str,
        tenant_id: str,
        user_id: str,
    ) -> bool:
        ...

    def add_message(
        self,
        *,
        message: ConversationMessage,
    ) -> ConversationMessage:
        ...

    def get_message_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> Optional[ConversationMessage]:
        ...

    def list_messages(
        self,
        *,
        session_id: str,
        tenant_id: str,
        user_id: str,
    ) -> list[ConversationMessage]:
        ...


class ConversationUseCases:
    def __init__(self, *, repo: ConversationRepositoryPort) -> None:
        self.repo = repo

    async def create_session(
        self,
        *,
        context: InternalContext,
        title: str,
        channel: str,
        mission: Optional[dict[str, Any]],
        client_context: dict[str, Any],
    ) -> ConversationSession:
        now = _utc_now()
        session = ConversationSession(
            id=f"chat_{uuid4().hex}",
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            title=title[:160] or "Nouvelle conversation",
            channel=channel or "workspace",
            status="active",
            turn_count=0,
            created_at=now,
            updated_at=now,
            mission=mission,
            client_context=client_context,
        )
        return self.repo.create_session(session=session)

    async def list_sessions(self, *, context: InternalContext) -> list[ConversationSession]:
        return self.repo.list_sessions(tenant_id=context.tenant_id, user_id=context.user_id)

    async def get_session(
        self,
        *,
        context: InternalContext,
        session_id: str,
    ) -> ConversationSession:
        session = self.repo.get_session(
            session_id=session_id,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
        )
        if not session:
            raise ConversationNotFoundError("session_not_found")
        return session

    async def delete_session(
        self,
        *,
        context: InternalContext,
        session_id: str,
    ) -> None:
        deleted = self.repo.delete_session(
            session_id=session_id,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
        )
        if not deleted:
            raise ConversationNotFoundError("session_not_found")

    async def add_message(
        self,
        *,
        context: InternalContext,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any],
        idempotency_key: str,
    ) -> ConversationMessage:
        if role not in ALLOWED_MESSAGE_ROLES:
            raise ConversationError("message_role_invalid")
        if not content.strip():
            raise ConversationError("message_content_empty")

        await self.get_session(context=context, session_id=session_id)
        existing = self.repo.get_message_by_idempotency_key(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            idempotency_key=idempotency_key,
        )
        if existing:
            return existing

        message = ConversationMessage(
            id=f"msg_{uuid4().hex}",
            session_id=session_id,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            role=role,
            content=content,
            created_at=_utc_now(),
            metadata=metadata,
            idempotency_key=idempotency_key,
        )
        return self.repo.add_message(message=message)

    async def list_messages(
        self,
        *,
        context: InternalContext,
        session_id: str,
    ) -> list[ConversationMessage]:
        await self.get_session(context=context, session_id=session_id)
        return self.repo.list_messages(
            session_id=session_id,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
        )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
