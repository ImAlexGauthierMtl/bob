"""Workflow routes — proxies to workflow~backend-api with B4F business logic."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.infrastructure.clients.platform_clients import workflow_client
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/workflows")


# ── Workflow CRUD ─────────────────────────────────

@router.get("")
async def list_workflows(
    request: Request,
    level: str = Query(None),
    module: str = Query(None),
    is_template: bool = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
):
    return await workflow_client.list(skip, limit, level, module, is_template, forward_headers=request.headers)


@router.post("", status_code=201)
async def create_workflow(data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await workflow_client.create(data, forward_headers=request.headers)


@router.get("/{wf_id}")
async def get_workflow(wf_id: str, request: Request, user: dict = Depends(get_current_user)):
    result = await workflow_client.get(wf_id, forward_headers=request.headers)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return result


@router.patch("/{wf_id}")
async def update_workflow(wf_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await workflow_client.update(wf_id, data, forward_headers=request.headers)


@router.delete("/{wf_id}", status_code=204)
async def delete_workflow(wf_id: str, request: Request, user: dict = Depends(get_current_user)):
    await workflow_client.delete(wf_id, forward_headers=request.headers)


# ── Steps ─────────────────────────────────────────

@router.get("/{wf_id}/steps")
async def list_steps(wf_id: str, request: Request, user: dict = Depends(get_current_user)):
    return await workflow_client.list_steps(wf_id, forward_headers=request.headers)


@router.post("/{wf_id}/steps", status_code=201)
async def add_step(wf_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await workflow_client.add_step(wf_id, data, forward_headers=request.headers)


@router.patch("/{wf_id}/steps/{step_id}")
async def update_step(wf_id: str, step_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await workflow_client.update_step(wf_id, step_id, data, forward_headers=request.headers)


@router.delete("/{wf_id}/steps/{step_id}", status_code=204)
async def delete_step(wf_id: str, step_id: str, request: Request, user: dict = Depends(get_current_user)):
    await workflow_client.delete_step(wf_id, step_id, forward_headers=request.headers)


# ── Executions ────────────────────────────────────

@router.post("/{wf_id}/run", status_code=201)
async def run_workflow(wf_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await workflow_client.create_execution(wf_id, data, forward_headers=request.headers)


@router.get("/{wf_id}/executions")
async def list_executions(
    wf_id: str,
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    return await workflow_client.list_executions(wf_id, limit, forward_headers=request.headers)


@router.get("/{wf_id}/executions/{exe_id}")
async def get_execution_detail(wf_id: str, exe_id: str, request: Request, user: dict = Depends(get_current_user)):
    result = await workflow_client.get_execution(wf_id, exe_id, forward_headers=request.headers)
    if not result:
        raise HTTPException(status_code=404, detail="Execution not found")
    return result


# ── Monitoring ────────────────────────────────────

@router.get("/monitoring/stats")
async def get_monitoring_stats(request: Request, user: dict = Depends(get_current_user)):
    return await workflow_client.get_monitoring_stats(forward_headers=request.headers)


@router.get("/monitoring/recent")
async def get_recent_executions(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    status_filter: str = Query(None, alias="status"),
    user: dict = Depends(get_current_user),
):
    return await workflow_client.get_recent_executions(limit, status_filter, forward_headers=request.headers)


# ── Override ──────────────────────────────────────

@router.post("/{wf_id}/override", status_code=201)
async def override_workflow(wf_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    parent = await workflow_client.get(wf_id, forward_headers=request.headers)
    if not parent:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if not parent.get("is_overridable", True):
        raise HTTPException(status_code=403, detail="This workflow does not allow overrides")

    level_rank = {"system": 0, "company": 1, "department": 2, "user": 3}
    target_level = data.get("target_level")
    if level_rank.get(target_level, 99) <= level_rank.get(parent.get("level"), 0):
        raise HTTPException(status_code=400, detail=f"Cannot override to same or higher level ({parent.get('level')} → {target_level})")

    clone_data = {
        "name": data.get("new_name") or f"{parent['name']} (Override)",
        "description": parent.get("description"),
        "level": target_level,
        "owner_id": data.get("owner_id") or user.get("user_id"),
        "owner_type": "user" if target_level == "user" else target_level,
        "trigger_type": parent.get("trigger_type"),
        "trigger_config": parent.get("trigger_config"),
        "execution_mode": data.get("execution_mode") or parent.get("execution_mode"),
        "required_capabilities": parent.get("required_capabilities"),
        "is_overridable": True,
        "override_policy": parent.get("override_policy"),
        "overrides_workflow_id": parent["id"],
        "module": parent.get("module"),
        "category": parent.get("category"),
        "steps": parent.get("steps", []),
    }
    return await workflow_client.create(clone_data, forward_headers=request.headers)
