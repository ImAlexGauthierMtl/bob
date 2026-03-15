"""Workflow Schemas — Pydantic models for Platform Services API."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class WorkflowStepCreate(BaseModel):
    """Create a workflow step."""
    name: str
    description: Optional[str] = None
    action_type: str
    config: Dict[str, Any]
    order: int


class WorkflowStepUpdate(BaseModel):
    """Update a workflow step."""
    name: Optional[str] = None
    description: Optional[str] = None
    action_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    order: Optional[int] = None


class WorkflowStepResponse(BaseModel):
    """A workflow step."""
    id: str
    name: str
    description: Optional[str] = None
    action_type: str
    config: Dict[str, Any]
    order: int
    
    class Config:
        from_attributes = True


class WorkflowCreate(BaseModel):
    """Create a workflow."""
    name: str
    description: Optional[str] = None
    steps: Optional[List[WorkflowStepCreate]] = None


class WorkflowUpdate(BaseModel):
    """Update a workflow."""
    name: Optional[str] = None
    description: Optional[str] = None


class WorkflowResponse(BaseModel):
    """A workflow."""
    id: str
    name: str
    description: Optional[str] = None
    steps: Optional[List[WorkflowStepResponse]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WorkflowListResponse(BaseModel):
    """List of workflows."""
    items: List[WorkflowResponse]
    total: int
    skip: int = 0
    limit: int = 50


class WorkflowRunRequest(BaseModel):
    """Request to run a workflow."""
    workflow_id: str
    input_data: Dict[str, Any]


class ExecutionDetailResponse(BaseModel):
    """Execution detail."""
    step_id: str
    step_name: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkflowStepExecutionResponse(BaseModel):
    """Workflow step execution response."""
    step_id: str
    step_name: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkflowExecutionResponse(BaseModel):
    """Workflow execution response."""
    id: str
    workflow_id: str
    status: str
    details: List[ExecutionDetailResponse]
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
