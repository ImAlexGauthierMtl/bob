"""Workflow schemas — Pydantic models for Workflow Backend API."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── Steps ──────────────────────────────────────────

class WorkflowStepCreate(BaseModel):
    name: str
    step_order: int = 0
    step_type: str
    agent_node: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    description: Optional[str] = None
    is_entry_point: bool = False


class WorkflowStepUpdate(BaseModel):
    name: Optional[str] = None
    step_order: Optional[int] = None
    step_type: Optional[str] = None
    agent_node: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    description: Optional[str] = None
    is_entry_point: Optional[bool] = None


class WorkflowStepResponse(BaseModel):
    id: str
    workflow_id: str
    name: str
    step_order: int
    step_type: str
    agent_node: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    description: Optional[str] = None
    is_entry_point: bool = False

    class Config:
        from_attributes = True


# ── Workflow ───────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    level: str = "company"
    owner_id: Optional[str] = None
    owner_type: Optional[str] = None
    trigger_type: str = "manual"
    trigger_config: Optional[Dict[str, Any]] = None
    execution_mode: str = "suggest"
    required_capabilities: Optional[List[str]] = None
    is_overridable: bool = True
    override_policy: str = "choice"
    overrides_workflow_id: Optional[str] = None
    module: Optional[str] = None
    category: Optional[str] = None
    is_template: bool = False
    steps: Optional[List[WorkflowStepCreate]] = None


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[Dict[str, Any]] = None
    execution_mode: Optional[str] = None
    required_capabilities: Optional[List[str]] = None
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
    trigger_config: Optional[Dict[str, Any]] = None
    execution_mode: str
    required_capabilities: Optional[List[str]] = None
    is_overridable: bool
    override_policy: str
    overrides_workflow_id: Optional[str] = None
    is_active: bool
    is_template: bool
    module: Optional[str] = None
    category: Optional[str] = None
    steps: Optional[List[WorkflowStepResponse]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkflowListResponse(BaseModel):
    items: List[WorkflowResponse]
    total: int
    skip: int = 0
    limit: int = 50


# ── Executions ─────────────────────────────────────

class WorkflowRunRequest(BaseModel):
    input_data: Optional[Dict[str, Any]] = None


class WorkflowStepExecutionResponse(BaseModel):
    id: str
    execution_id: str
    step_id: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    agent_mode_used: Optional[str] = None
    confidence_score: Optional[float] = None
    duration_ms: Optional[int] = None

    class Config:
        from_attributes = True


class WorkflowExecutionResponse(BaseModel):
    id: str
    workflow_id: str
    triggered_by: Optional[str] = None
    trigger_type: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    steps_completed: int = 0
    steps_total: int = 0
    duration_ms: Optional[int] = None

    class Config:
        from_attributes = True


class ExecutionDetailResponse(BaseModel):
    execution: WorkflowExecutionResponse
    steps: List[WorkflowStepExecutionResponse]
