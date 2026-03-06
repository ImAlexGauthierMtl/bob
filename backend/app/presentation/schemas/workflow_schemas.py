"""Workflow schemas — Pydantic models."""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ── Workflow Steps ────────────────────────────────

class WorkflowStepCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    step_order: int = 0
    step_type: str = Field(..., pattern="^(trigger|condition|action|ai_analysis|human_approval)$")
    agent_node: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    description: Optional[str] = None
    is_entry_point: bool = False


class WorkflowStepResponse(BaseModel):
    id: str
    workflow_id: str
    name: str
    step_order: int
    step_type: str
    agent_node: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    description: Optional[str] = None
    is_entry_point: bool

    class Config:
        from_attributes = True


class WorkflowStepUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    step_order: Optional[int] = None
    step_type: Optional[str] = None
    agent_node: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    description: Optional[str] = None
    is_entry_point: Optional[bool] = None


# ── Workflow ──────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    level: str = Field(..., pattern="^(system|company|department|user)$")
    owner_id: Optional[str] = None
    owner_type: Optional[str] = None
    trigger_type: str = "manual"
    trigger_config: Optional[dict[str, Any]] = None
    execution_mode: str = "suggest"
    required_capabilities: Optional[list[str]] = None
    is_overridable: bool = True
    override_policy: str = "choice"
    overrides_workflow_id: Optional[str] = None
    module: Optional[str] = None
    category: Optional[str] = None
    is_template: bool = False
    steps: Optional[List[WorkflowStepCreate]] = None


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[dict[str, Any]] = None
    execution_mode: Optional[str] = None
    required_capabilities: Optional[list[str]] = None
    is_overridable: Optional[bool] = None
    override_policy: Optional[str] = None
    is_active: Optional[bool] = None
    module: Optional[str] = None
    category: Optional[str] = None


class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    level: str
    owner_id: Optional[str] = None
    owner_type: Optional[str] = None
    trigger_type: str
    trigger_config: Optional[dict[str, Any]] = None
    execution_mode: str
    required_capabilities: Optional[list[str]] = None
    is_overridable: bool
    override_policy: str
    overrides_workflow_id: Optional[str] = None
    is_active: bool
    is_template: bool
    module: Optional[str] = None
    category: Optional[str] = None
    steps: List[WorkflowStepResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowListResponse(BaseModel):
    items: List[WorkflowResponse]
    total: int
    skip: int
    limit: int


# ── Execution ─────────────────────────────────────

class WorkflowExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    triggered_by: Optional[str] = None
    trigger_type: Optional[str] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    input_data: Optional[dict[str, Any]] = None
    output_data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    steps_completed: int
    steps_total: int
    duration_ms: Optional[int] = None

    class Config:
        from_attributes = True


class WorkflowStepExecutionResponse(BaseModel):
    id: str
    execution_id: str
    step_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    input_data: Optional[dict[str, Any]] = None
    output_data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    agent_mode_used: Optional[str] = None
    confidence_score: Optional[float] = None
    duration_ms: Optional[int] = None

    class Config:
        from_attributes = True


class ExecutionDetailResponse(BaseModel):
    execution: WorkflowExecutionResponse
    steps: List[WorkflowStepExecutionResponse]


class WorkflowRunRequest(BaseModel):
    input_data: Optional[dict[str, Any]] = None
