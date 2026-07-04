"""Tool governance routes for Bob Settings."""

from __future__ import annotations

import hashlib
import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.infrastructure.clients.agent_client import tool_governance_client
from app.middleware.auth import get_current_user
from shared.infrastructure import InternalSessionContext, InternalSessionContextSigner


router = APIRouter(prefix="/tool-governance")


@router.get("/policies")
async def list_tool_governance_policies(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return await _runtime_call(
        tool_governance_client.list_policies,
        headers=_runtime_headers(request=request, current_user=current_user),
    )


@router.put("/policies/{policy_id}")
async def update_tool_governance_policy(
    policy_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    data = await request.json()
    return await _runtime_call(
        tool_governance_client.update_policy,
        policy_id,
        data,
        headers=_runtime_headers(request=request, current_user=current_user),
    )


@router.get("/me")
async def get_my_tool_governance(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return await _runtime_call(
        tool_governance_client.get_my_access,
        headers=_runtime_headers(request=request, current_user=current_user),
    )


@router.put("/me/preferences")
async def update_my_tool_preferences(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    data = await request.json()
    return await _runtime_call(
        tool_governance_client.update_my_preferences,
        data,
        headers=_runtime_headers(request=request, current_user=current_user),
    )


async def _runtime_call(func, *args, headers: dict[str, str]) -> dict[str, Any]:
    try:
        return await func(*args, headers=headers)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=_safe_backend_detail(exc.response),
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "agent_runtime_backend_unavailable", "message": str(exc)},
        ) from exc


def _runtime_headers(*, request: Request, current_user: dict) -> dict[str, str]:
    trace_id = request.headers.get("x-trace-id") or hashlib.sha256(
        f"{current_user.get('user_id') or 'anonymous'}:{request.url.path}".encode("utf-8")
    ).hexdigest()[:32]
    context = InternalSessionContext(
        tenant_id=str(current_user.get("tenant_id") or "default"),
        user_id=str(current_user.get("user_id") or ""),
        session_id=request.headers.get("x-session-id") or "agent-control-settings",
        trace_id=trace_id,
        permissions=tuple(sorted(_as_set(current_user.get("permissions")) | _as_set(current_user.get("capabilities")))),
        entitlements=("agent_control.manage",),
        roles=tuple(sorted(_as_set(current_user.get("roles")))),
    )
    return {
        "X-Session-Context": _internal_session_signer().issue(context),
        "X-Trace-Id": trace_id,
    }


def _internal_session_signer() -> InternalSessionContextSigner:
    secret = os.environ.get("INTERNAL_SESSION_SECRET", "")
    if not secret and _is_development():
        secret = "dev-internal-session-secret-not-for-production"
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "internal_session_secret_missing"},
        )
    return InternalSessionContextSigner(
        secret,
        kid=os.environ.get("INTERNAL_SESSION_KID", "internal-session-dev"),
    )


def _safe_backend_detail(response: httpx.Response) -> Any:
    if not response.content:
        return {"code": "agent_runtime_backend_error"}
    try:
        payload = response.json()
    except ValueError:
        return {"code": "agent_runtime_backend_error", "message": response.text}
    return payload.get("detail", payload)


def _as_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {item.strip() for item in value.split(",") if item.strip()}
    if isinstance(value, (list, tuple, set)):
        return {str(item).strip() for item in value if str(item).strip()}
    return {str(value).strip()} if str(value).strip() else set()


def _is_development() -> bool:
    environment = os.environ.get("ENVIRONMENT", "development").strip().lower()
    return environment in {"development", "dev", "local", "test", "ci"}
