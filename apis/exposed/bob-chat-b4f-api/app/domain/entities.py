"""Domain entities for Bob Chat B4F orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


BOB_CHAT_CAPABILITY = "bob_chat.use"
DEFAULT_CHANNEL = "workspace"


@dataclass(frozen=True)
class BobChatMission:
    id: Optional[str] = None
    prompt: Optional[str] = None
    context: dict[str, Any] | None = None


@dataclass(frozen=True)
class BobChatMessageCommand:
    message: str
    session_id: Optional[str]
    channel: str
    mission: Optional[BobChatMission]
    client_context: dict[str, Any]


@dataclass(frozen=True)
class BobChatSecurityContext:
    tenant_id: str
    user_id: str
    session_id: str
    trace_id: str
    internal_session_context: str


@dataclass(frozen=True)
class ConversationSessionDraft:
    title: str
    channel: str
    mission: Optional[dict[str, Any]]
    client_context: dict[str, Any]


class BobChatError(Exception):
    """Base domain error for Bob Chat orchestration."""

    def __init__(self, code: str, *, status_code: int = 400, detail: Any | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.detail = detail if detail is not None else {"code": code}


class BobChatIntegrationError(BobChatError):
    """Raised when a required upstream service is unavailable or rejects a call."""


class BobChatNotFoundError(BobChatError):
    """Raised when a conversation resource cannot be found in scope."""
