"""SQLAlchemy repository for conversation data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.domain import ConversationMessage, ConversationSession
from app.infrastructure.persistence.models.conversation import (
    ConversationMessageModel,
    ConversationSessionModel,
)


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(self, *, session: ConversationSession) -> ConversationSession:
        model = ConversationSessionModel(
            id=session.id,
            tenant_id=session.tenant_id,
            user_id=session.user_id,
            title=session.title,
            channel=session.channel,
            status=session.status,
            turn_count=session.turn_count,
            mission=session.mission,
            client_context=session.client_context,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return _session_from_model(model)

    def list_sessions(self, *, tenant_id: str, user_id: str) -> list[ConversationSession]:
        models = (
            self.db.query(ConversationSessionModel)
            .filter(
                ConversationSessionModel.tenant_id == tenant_id,
                ConversationSessionModel.user_id == user_id,
                ConversationSessionModel.is_deleted.is_(False),
            )
            .order_by(ConversationSessionModel.updated_at.desc())
            .all()
        )
        return [_session_from_model(model) for model in models]

    def get_session(
        self,
        *,
        session_id: str,
        tenant_id: str,
        user_id: str,
    ) -> Optional[ConversationSession]:
        model = (
            self.db.query(ConversationSessionModel)
            .filter(
                ConversationSessionModel.id == session_id,
                ConversationSessionModel.tenant_id == tenant_id,
                ConversationSessionModel.user_id == user_id,
                ConversationSessionModel.is_deleted.is_(False),
            )
            .one_or_none()
        )
        return _session_from_model(model) if model else None

    def delete_session(self, *, session_id: str, tenant_id: str, user_id: str) -> bool:
        model = (
            self.db.query(ConversationSessionModel)
            .filter(
                ConversationSessionModel.id == session_id,
                ConversationSessionModel.tenant_id == tenant_id,
                ConversationSessionModel.user_id == user_id,
                ConversationSessionModel.is_deleted.is_(False),
            )
            .one_or_none()
        )
        if not model:
            return False
        model.is_deleted = True
        model.status = "deleted"
        model.deleted_at = datetime.now(timezone.utc)
        model.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return True

    def add_message(self, *, message: ConversationMessage) -> ConversationMessage:
        model = ConversationMessageModel(
            id=message.id,
            session_id=message.session_id,
            tenant_id=message.tenant_id,
            user_id=message.user_id,
            role=message.role,
            content=message.content,
            metadata_=message.metadata,
            idempotency_key=message.idempotency_key,
            created_at=message.created_at,
        )
        self.db.add(model)
        session_model = (
            self.db.query(ConversationSessionModel)
            .filter(ConversationSessionModel.id == message.session_id)
            .one()
        )
        if message.role == "user":
            session_model.turn_count += 1
        session_model.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(model)
        return _message_from_model(model)

    def get_message_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> Optional[ConversationMessage]:
        model = (
            self.db.query(ConversationMessageModel)
            .filter(
                ConversationMessageModel.tenant_id == tenant_id,
                ConversationMessageModel.user_id == user_id,
                ConversationMessageModel.idempotency_key == idempotency_key,
            )
            .one_or_none()
        )
        return _message_from_model(model) if model else None

    def list_messages(self, *, session_id: str, tenant_id: str, user_id: str) -> list[ConversationMessage]:
        models = (
            self.db.query(ConversationMessageModel)
            .filter(
                ConversationMessageModel.session_id == session_id,
                ConversationMessageModel.tenant_id == tenant_id,
                ConversationMessageModel.user_id == user_id,
            )
            .order_by(ConversationMessageModel.created_at.asc())
            .all()
        )
        return [_message_from_model(model) for model in models]


def _session_from_model(model: ConversationSessionModel) -> ConversationSession:
    return ConversationSession(
        id=model.id,
        tenant_id=model.tenant_id,
        user_id=model.user_id,
        title=model.title,
        channel=model.channel,
        status=model.status,
        turn_count=model.turn_count,
        created_at=model.created_at,
        updated_at=model.updated_at,
        mission=model.mission,
        client_context=model.client_context or {},
    )


def _message_from_model(model: ConversationMessageModel) -> ConversationMessage:
    return ConversationMessage(
        id=model.id,
        session_id=model.session_id,
        tenant_id=model.tenant_id,
        user_id=model.user_id,
        role=model.role,
        content=model.content,
        created_at=model.created_at,
        metadata=model.metadata_ or {},
        idempotency_key=model.idempotency_key,
    )
