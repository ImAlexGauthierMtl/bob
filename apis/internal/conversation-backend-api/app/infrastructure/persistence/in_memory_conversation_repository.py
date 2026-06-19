"""In-memory conversation repository for tests and contract probes."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Optional

from app.domain import ConversationMessage, ConversationSession


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self.sessions: dict[str, ConversationSession] = {}
        self.messages: dict[str, ConversationMessage] = {}
        self.deleted_session_ids: set[str] = set()

    def create_session(self, *, session: ConversationSession) -> ConversationSession:
        self.sessions[session.id] = session
        return session

    def list_sessions(self, *, tenant_id: str, user_id: str) -> list[ConversationSession]:
        sessions = [
            session
            for session in self.sessions.values()
            if session.tenant_id == tenant_id
            and session.user_id == user_id
            and session.id not in self.deleted_session_ids
        ]
        return sorted(sessions, key=lambda item: item.updated_at, reverse=True)

    def get_session(
        self,
        *,
        session_id: str,
        tenant_id: str,
        user_id: str,
    ) -> Optional[ConversationSession]:
        session = self.sessions.get(session_id)
        if not session or session.id in self.deleted_session_ids:
            return None
        if session.tenant_id != tenant_id or session.user_id != user_id:
            return None
        return session

    def delete_session(self, *, session_id: str, tenant_id: str, user_id: str) -> bool:
        session = self.get_session(session_id=session_id, tenant_id=tenant_id, user_id=user_id)
        if not session:
            return False
        self.deleted_session_ids.add(session_id)
        self.sessions[session_id] = replace(
            session,
            status="deleted",
            updated_at=datetime.now(timezone.utc),
        )
        return True

    def add_message(self, *, message: ConversationMessage) -> ConversationMessage:
        self.messages[message.id] = message
        session = self.sessions[message.session_id]
        turn_count = session.turn_count + 1 if message.role == "user" else session.turn_count
        self.sessions[message.session_id] = replace(
            session,
            turn_count=turn_count,
            updated_at=datetime.now(timezone.utc),
        )
        return message

    def get_message_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> Optional[ConversationMessage]:
        for message in self.messages.values():
            if (
                message.tenant_id == tenant_id
                and message.user_id == user_id
                and message.idempotency_key == idempotency_key
            ):
                return message
        return None

    def list_messages(self, *, session_id: str, tenant_id: str, user_id: str) -> list[ConversationMessage]:
        messages = [
            message
            for message in self.messages.values()
            if message.session_id == session_id
            and message.tenant_id == tenant_id
            and message.user_id == user_id
        ]
        return sorted(messages, key=lambda item: item.created_at)
