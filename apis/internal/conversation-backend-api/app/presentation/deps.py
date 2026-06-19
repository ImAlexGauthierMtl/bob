"""Presentation dependencies for Conversation Backend."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.application.use_cases.conversation_use_cases import ConversationUseCases
from app.domain import InternalContext
from app.infrastructure.database import get_db
from app.infrastructure.persistence.conversation_repository import ConversationRepository


def get_internal_context(request: Request) -> InternalContext:
    context = getattr(request.state, "internal_session_context", None)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "internal_session_missing"},
        )
    return InternalContext(
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        trace_id=context.trace_id,
        permissions=context.permissions,
        roles=context.roles,
    )


def get_conversation_use_cases(db: Session = Depends(get_db)) -> ConversationUseCases:
    return ConversationUseCases(repo=ConversationRepository(db))
