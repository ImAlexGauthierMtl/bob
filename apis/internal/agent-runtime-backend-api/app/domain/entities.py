"""Agent Runtime domain entities."""

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
class AgentRun:
    id: str
    tenant_id: str
    user_id: str
    session_id: str
    input_message_id: str
    status: str
    mode: str
    trace_id: str
    assistant_content: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    narration_steps: list[dict[str, Any]] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class AgentConfirmation:
    id: str
    run_id: str
    tenant_id: str
    user_id: str
    status: str
    label: str
    created_at: datetime
    resolved_at: Optional[datetime] = None


@dataclass(frozen=True)
class AgentConfirmationResolution:
    confirmation: AgentConfirmation
    execution: Optional[dict[str, Any]] = None
    run: Optional[AgentRun] = None


@dataclass(frozen=True)
class RuntimeToolCall:
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeModelResult:
    content: str
    provider: str
    model: str
    mode: str
    tool_calls: list[RuntimeToolCall] = field(default_factory=list)
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeToolResult:
    call_id: str
    name: str
    status: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeCatalogItem:
    id: str
    tenant_id: str
    user_id: str
    collection: str
    name: str
    payload: dict[str, Any]
    payload_hash: str
    created_at: datetime
    idempotency_key: Optional[str] = None


class AgentRuntimeError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class AgentRuntimeNotFoundError(AgentRuntimeError):
    """Raised when a run or confirmation is missing or outside scope."""
