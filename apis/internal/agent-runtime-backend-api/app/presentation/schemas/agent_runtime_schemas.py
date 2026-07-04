"""HTTP schemas for Agent Runtime routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain import AgentConfirmation, AgentConfirmationResolution, AgentRun


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
    execution: dict[str, Any] | None = None
    run: RunResponse | None = None

    @classmethod
    def from_domain(
        cls,
        confirmation: AgentConfirmation,
        *,
        execution: dict[str, Any] | None = None,
        run: AgentRun | None = None,
    ) -> "ConfirmationResponse":
        return cls(
            id=confirmation.id,
            run_id=confirmation.run_id,
            status=confirmation.status,
            label=confirmation.label,
            created_at=confirmation.created_at,
            resolved_at=confirmation.resolved_at,
            execution=execution,
            run=RunResponse.from_domain(run) if run else None,
        )

    @classmethod
    def from_resolution(cls, resolution: AgentConfirmationResolution) -> "ConfirmationResponse":
        return cls.from_domain(
            resolution.confirmation,
            execution=resolution.execution,
            run=resolution.run,
        )


class RuntimeCatalogItemCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=180)
    id: str | None = Field(default=None, max_length=64)
    description: str | None = None
    provider_id: str | None = None
    status: str | None = None
    skills: list[str] | None = None
    tools: list[str] | None = None
    scope: str | None = None
    family: str | None = None
    risk: str | None = None
    execution: str | None = None
    servers: list[str] | None = None
    skill: str | None = None
    capabilities: str | None = None
    source: str | None = Field(default=None, max_length=240)

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class ToolGovernancePolicyRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=180)
    provider: str | None = Field(default=None, max_length=80)
    integration_key: str | None = Field(default=None, max_length=120)
    tool_key: str | None = Field(default=None, max_length=180)
    family: str | None = Field(default=None, max_length=120)
    capability: str | None = Field(default=None, max_length=180)
    risk: str | None = Field(default=None, max_length=80)
    enabled: bool = True
    team_scope: list[str] = Field(default_factory=list)
    sync_enabled: bool = False
    sync_mode: str = Field("none", max_length=40)
    data_mapping: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class UserToolPreferencesRequest(BaseModel):
    preferred_email_provider: str | None = Field(default=None, max_length=80)
    preferred_calendar_provider: str | None = Field(default=None, max_length=80)
    require_write_confirmation: bool | None = None
    show_tool_trace: bool | None = None
    allow_personal_connectors: bool | None = None
