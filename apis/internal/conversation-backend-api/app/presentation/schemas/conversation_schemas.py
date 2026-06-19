"""HTTP schemas for conversation routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.domain import ConversationMessage, ConversationSession


class SessionCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    channel: str = Field("workspace", min_length=1, max_length=50)
    mission: Optional[dict[str, Any]] = None
    client_context: dict[str, Any] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    id: str
    title: str
    channel: str
    status: str
    turn_count: int
    created_at: datetime
    updated_at: datetime
    mission: Optional[dict[str, Any]] = None
    client_context: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, session: ConversationSession) -> "SessionResponse":
        return cls(
            id=session.id,
            title=session.title,
            channel=session.channel,
            status=session.status,
            turn_count=session.turn_count,
            created_at=session.created_at,
            updated_at=session.updated_at,
            mission=session.mission,
            client_context=session.client_context,
        )


class SessionListResponse(BaseModel):
    items: list[SessionResponse]


class MessageCreateRequest(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, max_length=12000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, message: ConversationMessage) -> "MessageResponse":
        return cls(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            metadata=message.metadata,
        )


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
