"""Workflow CRUD routes — pure storage, no business logic."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.workflow_repository import WorkflowRepository
from app.domain.entities.workflow import Workflow, WorkflowStep
from app.domain.entities.workflow_execution import WorkflowExecution, WorkflowStepExecution
from app.events.publishers import publish_workflow_created, publish_workflow_updated, publish_workflow_deleted, publish_workflow_executed
from app.presentation.schemas.workflow_schemas import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse, WorkflowListResponse,
    WorkflowStepCreate, WorkflowStepUpdate, WorkflowStepResponse,
    WorkflowRunRequest, WorkflowExecutionResponse, ExecutionDetailResponse,
    WorkflowStepExecutionResponse,
)

router = APIRouter(prefix="/api/v1/workflows")


# ── Workflow CRUD ─────────────────────────────────

@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = WorkflowRepository(db)
    wf = Workflow(
        name=data.name,
        description=data.description,
        level=data.level,
        owner_id=data.owner_id or user.get("user_id"),
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
        tenant_id=user["tenant_id"],
        created_by=user["email"],
    )
    wf = repo.create(wf)

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

    steps = repo.get_steps(wf.id)
    await publish_workflow_created(wf.id, {"name": wf.name, "tenant_id": wf.tenant_id})
    return _workflow_to_response(wf, steps)


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    level: str = Query(None),
    module: str = Query(None),
    is_template: bool = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = WorkflowRepository(db)
    items = repo.list_all(user["tenant_id"], level, module, is_template, skip, limit)
    total = repo.count(user["tenant_id"], level)

    response_items = []
    for wf in items:
        steps = repo.get_steps(wf.id)
        response_items.append(_workflow_to_response(wf, steps))

    return WorkflowListResponse(items=response_items, total=total, skip=skip, limit=limit)


@router.get("/{wf_id}", response_model=WorkflowResponse)
async def get_workflow(
    wf_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = WorkflowRepository(db)
    wf = repo.get_by_id(wf_id, user["tenant_id"])
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    steps = repo.get_steps(wf.id)
    return _workflow_to_response(wf, steps)


@router.patch("/{wf_id}", response_model=WorkflowResponse)
async def update_workflow(
    wf_id: str,
    data: WorkflowUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = WorkflowRepository(db)
    wf = repo.get_by_id(wf_id, user["tenant_id"])
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(wf, key, value)
    wf.updated_by = user["email"]
    wf = repo.update(wf)
    steps = repo.get_steps(wf.id)
    await publish_workflow_updated(wf.id, {"fields": list(update_data.keys())})
    return _workflow_to_response(wf, steps)


@router.delete("/{wf_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    wf_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = WorkflowRepository(db)
    wf = repo.get_by_id(wf_id, user["tenant_id"])
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    repo.soft_delete(wf, user["email"])
    await publish_workflow_deleted(wf_id)


# ── Steps ─────────────────────────────────────────

@router.get("/{wf_id}/steps", response_model=list[WorkflowStepResponse])
async def list_steps(
    wf_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = WorkflowRepository(db)
    wf = repo.get_by_id(wf_id, user["tenant_id"])
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    steps = repo.get_steps(wf_id)
    return [WorkflowStepResponse.model_validate(s) for s in steps]


@router.post("/{wf_id}/steps", response_model=WorkflowStepResponse, status_code=status.HTTP_201_CREATED)
async def add_step(
    wf_id: str,
    data: WorkflowStepCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = WorkflowRepository(db)
    wf = repo.get_by_id(wf_id, user["tenant_id"])
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
    created = repo.add_step(step)
    return WorkflowStepResponse.model_validate(created)


@router.patch("/{wf_id}/steps/{step_id}", response_model=WorkflowStepResponse)
async def update_step(
    wf_id: str,
    step_id: str,
    data: WorkflowStepUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = WorkflowRepository(db)
    step = repo.get_step_by_id(step_id)
    if not step or step.workflow_id != wf_id:
        raise HTTPException(status_code=404, detail="Step not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(step, key, value)
    updated = repo.update_step(step)
    return WorkflowStepResponse.model_validate(updated)


@router.delete("/{wf_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(
    wf_id: str,
    step_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = WorkflowRepository(db)
    step = repo.get_step_by_id(step_id)
    if not step or step.workflow_id != wf_id:
        raise HTTPException(status_code=404, detail="Step not found")
    repo.delete_step(step_id)


# ── Executions ────────────────────────────────────

@router.post("/{wf_id}/executions", response_model=WorkflowExecutionResponse, status_code=status.HTTP_201_CREATED)
async def create_execution(
    wf_id: str,
    data: WorkflowRunRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = WorkflowRepository(db)
    wf = repo.get_by_id(wf_id, user["tenant_id"])
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    steps = repo.get_steps(wf_id)
    exe = WorkflowExecution(
        workflow_id=wf_id,
        triggered_by=user["email"],
        trigger_type="manual",
        input_data=data.input_data,
        steps_total=len(steps),
        tenant_id=user["tenant_id"],
    )
    created = repo.create_execution(exe)
    await publish_workflow_executed(wf_id, created.id, {"triggered_by": user["email"]})
    return WorkflowExecutionResponse.model_validate(created)


@router.get("/{wf_id}/executions", response_model=list[WorkflowExecutionResponse])
async def list_executions(
    wf_id: str,
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = WorkflowRepository(db)
    return [WorkflowExecutionResponse.model_validate(e) for e in repo.list_executions(wf_id, limit)]


@router.get("/{wf_id}/executions/{exe_id}", response_model=ExecutionDetailResponse)
async def get_execution_detail(
    wf_id: str,
    exe_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = WorkflowRepository(db)
    exe = repo.get_execution(exe_id)
    if not exe or exe.workflow_id != wf_id:
        raise HTTPException(status_code=404, detail="Execution not found")

    step_exes = repo.get_step_executions(exe_id)
    return ExecutionDetailResponse(
        execution=WorkflowExecutionResponse.model_validate(exe),
        steps=[WorkflowStepExecutionResponse.model_validate(s) for s in step_exes],
    )


@router.patch("/{wf_id}/executions/{exe_id}", response_model=WorkflowExecutionResponse)
async def update_execution(
    wf_id: str,
    exe_id: str,
    data: dict,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = WorkflowRepository(db)
    exe = repo.get_execution(exe_id)
    if not exe or exe.workflow_id != wf_id:
        raise HTTPException(status_code=404, detail="Execution not found")

    for key, value in data.items():
        if hasattr(exe, key):
            setattr(exe, key, value)
    updated = repo.update_execution(exe)
    return WorkflowExecutionResponse.model_validate(updated)


# ── Monitoring ────────────────────────────────────

@router.get("/monitoring/stats")
async def get_monitoring_stats(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant_id = user["tenant_id"]

    stats = db.query(
        func.count(WorkflowExecution.id).label("total"),
        func.count(WorkflowExecution.id).filter(WorkflowExecution.status == "completed").label("completed"),
        func.count(WorkflowExecution.id).filter(WorkflowExecution.status == "failed").label("failed"),
        func.count(WorkflowExecution.id).filter(WorkflowExecution.status == "running").label("running"),
        func.count(WorkflowExecution.id).filter(WorkflowExecution.status == "pending_approval").label("pending"),
        func.avg(WorkflowExecution.duration_ms).label("avg_duration_ms"),
    ).filter(WorkflowExecution.tenant_id == tenant_id).first()

    repo = WorkflowRepository(db)
    workflows = repo.list_all(tenant_id, skip=0, limit=500)
    active_count = sum(1 for wf in workflows if wf.is_active)

    return {
        "total_executions": stats.total or 0,
        "completed": stats.completed or 0,
        "failed": stats.failed or 0,
        "running": stats.running or 0,
        "pending_approval": stats.pending or 0,
        "avg_duration_ms": round(stats.avg_duration_ms, 1) if stats.avg_duration_ms else 0,
        "success_rate": round((stats.completed / stats.total) * 100, 1) if stats.total else 0,
        "total_workflows": len(workflows),
        "active_workflows": active_count,
    }


@router.get("/monitoring/recent")
async def get_recent_executions(
    limit: int = Query(20, ge=1, le=100),
    status_filter: str = Query(None, alias="status"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(WorkflowExecution).filter(
        WorkflowExecution.tenant_id == user["tenant_id"],
    )
    if status_filter:
        query = query.filter(WorkflowExecution.status == status_filter)

    exes = query.order_by(WorkflowExecution.started_at.desc()).limit(limit).all()

    return [
        {
            "id": e.id,
            "workflow_id": e.workflow_id,
            "status": e.status,
            "triggered_by": e.triggered_by,
            "steps_completed": e.steps_completed,
            "steps_total": e.steps_total,
            "duration_ms": e.duration_ms,
            "error": e.error,
            "started_at": str(e.started_at) if e.started_at else None,
            "completed_at": str(e.completed_at) if e.completed_at else None,
        }
        for e in exes
    ]


# ── Helper ────────────────────────────────────────

def _workflow_to_response(wf: Workflow, steps: list) -> WorkflowResponse:
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
