"""HTTP schemas for Agent Runtime routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain import AgentConfirmation, AgentRun


class RunCreateRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    input_message_id: str = Field(..., min_length=1, max_length=64)
    prompt: str = Field(..., min_length=1, max_length=12000)
    channel: str = Field("workspace", min_length=1, max_length=50)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    id: str
    session_id: str
    input_message_id: str
    status: str
    mode: str
    trace_id: str
    assistant_content: str
    created_at: datetime
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    narration_steps: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, run: AgentRun) -> "RunResponse":
        return cls(
            id=run.id,
            session_id=run.session_id,
            input_message_id=run.input_message_id,
            status=run.status,
            mode=run.mode,
            trace_id=run.trace_id,
            assistant_content=run.assistant_content,
            created_at=run.created_at,
            completed_at=run.completed_at,
            cancelled_at=run.cancelled_at,
            metadata=run.metadata,
            narration_steps=run.narration_steps,
            actions=run.actions,
            artifacts=run.artifacts,
        )


class ConfirmationResponse(BaseModel):
    id: str
    run_id: str
    status: str
    label: str
    created_at: datetime
    resolved_at: datetime | None = None

    @classmethod
    def from_domain(cls, confirmation: AgentConfirmation) -> "ConfirmationResponse":
        return cls(
            id=confirmation.id,
            run_id=confirmation.run_id,
            status=confirmation.status,
            label=confirmation.label,
            created_at=confirmation.created_at,
            resolved_at=confirmation.resolved_at,
        )
