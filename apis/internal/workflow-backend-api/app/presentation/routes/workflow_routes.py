"""Workflow CRUD routes — pure storage, no business logic."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.use_cases.workflow_use_cases import WorkflowUseCases
from app.domain.exceptions import (
    WorkflowExecutionNotFoundError,
    WorkflowNotFoundError,
    WorkflowStepNotFoundError,
)
from app.middleware.auth import get_current_user
from app.presentation.deps import get_workflow_use_cases
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
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    result = await use_cases.create_workflow(data.model_dump(), user)
    return _workflow_to_response(result.workflow, result.steps)


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    level: str = Query(None),
    module: str = Query(None),
    is_template: bool = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    result = await use_cases.list_workflows(user["tenant_id"], level, module, is_template, skip, limit)
    return WorkflowListResponse(
        items=[_workflow_to_response(item.workflow, item.steps) for item in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.get("/{wf_id}", response_model=WorkflowResponse)
async def get_workflow(
    wf_id: str,
    user: dict = Depends(get_current_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    try:
        result = await use_cases.get_workflow(wf_id, user["tenant_id"])
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return _workflow_to_response(result.workflow, result.steps)


@router.patch("/{wf_id}", response_model=WorkflowResponse)
async def update_workflow(
    wf_id: str,
    data: WorkflowUpdate,
    user: dict = Depends(get_current_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    try:
        result = await use_cases.update_workflow(wf_id, data.model_dump(exclude_unset=True), user)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return _workflow_to_response(result.workflow, result.steps)


@router.delete("/{wf_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    wf_id: str,
    user: dict = Depends(get_current_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    try:
        await use_cases.delete_workflow(wf_id, user)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")


# ── Steps ─────────────────────────────────────────

@router.get("/{wf_id}/steps", response_model=list[WorkflowStepResponse])
async def list_steps(
    wf_id: str,
    user: dict = Depends(get_current_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    try:
        steps = await use_cases.list_steps(wf_id, user)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return [WorkflowStepResponse.model_validate(s) for s in steps]


@router.post("/{wf_id}/steps", response_model=WorkflowStepResponse, status_code=status.HTTP_201_CREATED)
async def add_step(
    wf_id: str,
    data: WorkflowStepCreate,
    user: dict = Depends(get_current_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    try:
        created = await use_cases.add_step(wf_id, data.model_dump(), user)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowStepResponse.model_validate(created)


@router.patch("/{wf_id}/steps/{step_id}", response_model=WorkflowStepResponse)
async def update_step(
    wf_id: str,
    step_id: str,
    data: WorkflowStepUpdate,
    user: dict = Depends(get_current_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    try:
        updated = await use_cases.update_step(wf_id, step_id, data.model_dump(exclude_unset=True))
    except WorkflowStepNotFoundError:
        raise HTTPException(status_code=404, detail="Step not found")
    return WorkflowStepResponse.model_validate(updated)


@router.delete("/{wf_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(
    wf_id: str,
    step_id: str,
    user: dict = Depends(get_current_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    try:
        await use_cases.delete_step(wf_id, step_id)
    except WorkflowStepNotFoundError:
        raise HTTPException(status_code=404, detail="Step not found")


# ── Executions ────────────────────────────────────

@router.post("/{wf_id}/executions", response_model=WorkflowExecutionResponse, status_code=status.HTTP_201_CREATED)
async def create_execution(
    wf_id: str,
    data: WorkflowRunRequest,
    user: dict = Depends(get_current_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    try:
        created = await use_cases.create_execution(wf_id, data.model_dump(), user)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowExecutionResponse.model_validate(created)


@router.get("/{wf_id}/executions", response_model=list[WorkflowExecutionResponse])
async def list_executions(
    wf_id: str,
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    executions = await use_cases.list_executions(wf_id, limit)
    return [WorkflowExecutionResponse.model_validate(e) for e in executions]


@router.get("/{wf_id}/executions/{exe_id}", response_model=ExecutionDetailResponse)
async def get_execution_detail(
    wf_id: str,
    exe_id: str,
    user: dict = Depends(get_current_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    try:
        result = await use_cases.get_execution_detail(wf_id, exe_id)
    except WorkflowExecutionNotFoundError:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ExecutionDetailResponse(
        execution=WorkflowExecutionResponse.model_validate(result.execution),
        steps=[WorkflowStepExecutionResponse.model_validate(s) for s in result.steps],
    )


@router.patch("/{wf_id}/executions/{exe_id}", response_model=WorkflowExecutionResponse)
async def update_execution(
    wf_id: str,
    exe_id: str,
    data: dict,
    user: dict = Depends(get_current_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    try:
        updated = await use_cases.update_execution(wf_id, exe_id, data)
    except WorkflowExecutionNotFoundError:
        raise HTTPException(status_code=404, detail="Execution not found")
    return WorkflowExecutionResponse.model_validate(updated)


# ── Monitoring ────────────────────────────────────

@router.get("/monitoring/stats")
async def get_monitoring_stats(
    user: dict = Depends(get_current_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    return await use_cases.get_monitoring_stats(user["tenant_id"])


@router.get("/monitoring/recent")
async def get_recent_executions(
    limit: int = Query(20, ge=1, le=100),
    status_filter: str = Query(None, alias="status"),
    user: dict = Depends(get_current_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    return await use_cases.get_recent_executions(user["tenant_id"], limit, status_filter)


# ── Helper ────────────────────────────────────────

def _workflow_to_response(wf, steps: list) -> WorkflowResponse:
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
