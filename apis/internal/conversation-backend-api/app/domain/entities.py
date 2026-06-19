"""Conversation domain entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True)
class InternalContext:
    tenant_id: str
    user_id: str
    trace_id: str
    permissions: tuple[str, ...] = field(default_factory=tuple)
    roles: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ConversationSession:
    id: str
    tenant_id: str
    user_id: str
    title: str
    channel: str
    status: str
    turn_count: int
    created_at: datetime
    updated_at: datetime
    mission: Optional[dict[str, Any]] = None
    client_context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConversationMessage:
    id: str
    session_id: str
    tenant_id: str
    user_id: str
    role: str
    content: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    idempotency_key: Optional[str] = None


class ConversationError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ConversationNotFoundError(ConversationError):
    """Raised when a session is missing or outside tenant/user scope."""
