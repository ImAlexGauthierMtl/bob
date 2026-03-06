"""Workflow routes — CRUD + execution."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import structlog

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.infrastructure.persistence.workflow_repository import WorkflowRepository
from app.infrastructure.persistence.user_repository import UserRepository
from app.domain.entities.workflow import Workflow, WorkflowStep
from app.agents.workflow_runner import WorkflowRunner
from app.presentation.schemas.workflow_schemas import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowStepCreate,
    WorkflowStepUpdate,
    WorkflowStepResponse,
    WorkflowRunRequest,
    WorkflowExecutionResponse,
    ExecutionDetailResponse,
    WorkflowStepExecutionResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/workflows")


# ── Workflow CRUD ─────────────────────────────────

@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new workflow with optional inline steps."""
    repo = WorkflowRepository(db)

    wf = Workflow(
        name=data.name,
        description=data.description,
        level=data.level,
        owner_id=data.owner_id or current_user.get("user_id"),
        owner_type=data.owner_type or "user",
        trigger_type=data.trigger_type,
        trigger_config=data.trigger_config,
        execution_mode=data.execution_mode,
        required_capabilities=data.required_capabilities,
        is_overridable=data.is_overridable,
        override_policy=data.override_policy,
        overrides_workflow_id=data.overrides_workflow_id,
        module=data.module,
        category=data.category,
        is_template=data.is_template,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
    )
    wf = repo.create(wf)

    # Create inline steps if provided
    if data.steps:
        for step_data in data.steps:
            step = WorkflowStep(
                workflow_id=wf.id,
                name=step_data.name,
                step_order=step_data.step_order,
                step_type=step_data.step_type,
                agent_node=step_data.agent_node,
                config=step_data.config,
                on_success=step_data.on_success,
                on_failure=step_data.on_failure,
                description=step_data.description,
                is_entry_point=step_data.is_entry_point,
            )
            repo.add_step(step)

    # Return with steps
    steps = repo.get_steps(wf.id)
    return _workflow_to_response(wf, steps)


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    level: str = Query(None),
    module: str = Query(None),
    is_template: bool = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List workflows with filters."""
    repo = WorkflowRepository(db)
    items = repo.list_all(current_user["tenant_id"], level, module, is_template, skip, limit)
    total = repo.count(current_user["tenant_id"], level)

    response_items = []
    for wf in items:
        steps = repo.get_steps(wf.id)
        response_items.append(_workflow_to_response(wf, steps))

    return WorkflowListResponse(items=response_items, total=total, skip=skip, limit=limit)


@router.get("/{wf_id}", response_model=WorkflowResponse)
async def get_workflow(
    wf_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a workflow by ID, including its steps."""
    repo = WorkflowRepository(db)
    wf = repo.get_by_id(wf_id, current_user["tenant_id"])
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    steps = repo.get_steps(wf.id)
    return _workflow_to_response(wf, steps)


@router.patch("/{wf_id}", response_model=WorkflowResponse)
async def update_workflow(
    wf_id: str,
    data: WorkflowUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a workflow."""
    repo = WorkflowRepository(db)
    wf = repo.get_by_id(wf_id, current_user["tenant_id"])
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.level == "system":
        raise HTTPException(status_code=403, detail="System workflows cannot be modified")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(wf, key, value)
    wf.updated_by = current_user["email"]
    wf = repo.update(wf)
    steps = repo.get_steps(wf.id)
    return _workflow_to_response(wf, steps)


@router.delete("/{wf_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    wf_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft delete a workflow."""
    repo = WorkflowRepository(db)
    wf = repo.get_by_id(wf_id, current_user["tenant_id"])
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.level == "system":
        raise HTTPException(status_code=403, detail="System workflows cannot be deleted")
    repo.soft_delete(wf, current_user["email"])


# ── Steps ─────────────────────────────────────────

@router.post("/{wf_id}/steps", response_model=WorkflowStepResponse, status_code=status.HTTP_201_CREATED)
async def add_step(
    wf_id: str,
    data: WorkflowStepCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a step to a workflow."""
    repo = WorkflowRepository(db)
    wf = repo.get_by_id(wf_id, current_user["tenant_id"])
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    step = WorkflowStep(
        workflow_id=wf_id,
        name=data.name,
        step_order=data.step_order,
        step_type=data.step_type,
        agent_node=data.agent_node,
        config=data.config,
        on_success=data.on_success,
        on_failure=data.on_failure,
        description=data.description,
        is_entry_point=data.is_entry_point,
    )
    return repo.add_step(step)


@router.patch("/{wf_id}/steps/{step_id}", response_model=WorkflowStepResponse)
async def update_step(
    wf_id: str,
    step_id: str,
    data: WorkflowStepUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a workflow step."""
    repo = WorkflowRepository(db)
    step = repo.get_step_by_id(step_id)
    if not step or step.workflow_id != wf_id:
        raise HTTPException(status_code=404, detail="Step not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(step, key, value)
    return repo.update_step(step)


@router.delete("/{wf_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(
    wf_id: str,
    step_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a workflow step."""
    repo = WorkflowRepository(db)
    step = repo.get_step_by_id(step_id)
    if not step or step.workflow_id != wf_id:
        raise HTTPException(status_code=404, detail="Step not found")
    repo.delete_step(step_id)


# ── Run ───────────────────────────────────────────

@router.post("/{wf_id}/run", response_model=WorkflowExecutionResponse)
async def run_workflow(
    wf_id: str,
    data: WorkflowRunRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute a workflow."""
    repo = WorkflowRepository(db)
    user_repo = UserRepository(db)

    wf = repo.get_by_id(wf_id, current_user["tenant_id"])
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if not wf.is_active:
        raise HTTPException(status_code=400, detail="Workflow is not active")

    user = user_repo.get_by_email(current_user["email"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    runner = WorkflowRunner(db)
    try:
        execution = await runner.run(
            workflow=wf,
            user=user,
            tenant_id=current_user["tenant_id"],
            input_data=data.input_data,
            triggered_by=current_user["email"],
        )
        return execution
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Executions ────────────────────────────────────

@router.get("/{wf_id}/executions", response_model=list[WorkflowExecutionResponse])
async def list_executions(
    wf_id: str,
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent executions of a workflow."""
    repo = WorkflowRepository(db)
    return repo.list_executions(wf_id, limit)


@router.get("/{wf_id}/executions/{exe_id}", response_model=ExecutionDetailResponse)
async def get_execution_detail(
    wf_id: str,
    exe_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed execution with step-level logs."""
    repo = WorkflowRepository(db)
    exe = repo.get_execution(exe_id)
    if not exe or exe.workflow_id != wf_id:
        raise HTTPException(status_code=404, detail="Execution not found")

    step_exes = repo.get_step_executions(exe_id)
    return ExecutionDetailResponse(
        execution=exe,
        steps=step_exes,
    )


# ── Helper ────────────────────────────────────────

def _workflow_to_response(wf: Workflow, steps: list) -> WorkflowResponse:
    """Map workflow + steps to response model."""
    return WorkflowResponse(
        id=wf.id,
        name=wf.name,
        description=wf.description,
        level=wf.level,
        owner_id=wf.owner_id,
        owner_type=wf.owner_type,
        trigger_type=wf.trigger_type,
        trigger_config=wf.trigger_config,
        execution_mode=wf.execution_mode,
        required_capabilities=wf.required_capabilities,
        is_overridable=wf.is_overridable,
        override_policy=wf.override_policy,
        overrides_workflow_id=wf.overrides_workflow_id,
        is_active=wf.is_active,
        is_template=wf.is_template,
        module=wf.module,
        category=wf.category,
        steps=[WorkflowStepResponse.model_validate(s) for s in steps],
        created_at=wf.created_at,
        updated_at=wf.updated_at,
    )
