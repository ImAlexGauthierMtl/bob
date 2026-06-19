"""Bob Cloud-backed auth routes with local/dev JWT fallback.

These routes run in parallel with the legacy `/auth/*` JWT flow until the
frontend cutover is explicit.
"""

import os
from typing import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
import httpx

from app.application.use_cases.auth_use_cases import AuthError
from app.presentation.routes.auth_routes import get_auth_use_cases
from shared.services import (
    BobCloudClient,
    BobCloudModeError,
    BobCloudResponseError,
    create_bob_cloud_client_from_env,
)

router = APIRouter(prefix="/api/auth/v1")


def _local_auth_enabled() -> bool:
    configured = os.environ.get("CDE_LOCAL_AUTH_ENABLED")
    if configured is not None:
        return configured.lower() in {"1", "true", "yes", "on"}
    return os.environ.get("ENVIRONMENT", "development").lower() in {"development", "dev", "local", "test"}


def _bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


async def _local_session(request: Request) -> dict | None:
    token = _bearer_token(request)
    if not token or not _local_auth_enabled():
        return None

    auth = get_auth_use_cases()
    try:
        current = await auth.current_user(token, forward_headers=request.headers)
        user = await auth.get_me(current["user_id"], forward_headers=request.headers)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    roles = [role for role in current.get("roles", []) if role]
    if user.get("is_super_admin") and "admin" not in roles:
        roles.insert(0, "admin")

    tenant_id = user.get("tenant_id") or current.get("tenant_id") or user.get("active_organization_id") or "default"
    tenant_name = user.get("active_organization_name") or "Local development"
    return {
        "authenticated": True,
        "session_id": f"local-{user['id']}",
        "user": {
            "id": user["id"],
            "email": user.get("email", ""),
            "display_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "status": user.get("status", "ACTIVE"),
        },
        "tenant": {
            "id": tenant_id,
            "name": tenant_name,
            "status": "ACTIVE",
            "scope": "local-dev",
        },
        "permissions": current.get("permissions", []),
        "platform_roles": roles or [user.get("role", "member")],
        "source": "local-dev",
    }


def get_bob_cloud_client() -> BobCloudClient:
    try:
        return create_bob_cloud_client_from_env()
    except BobCloudModeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "bob_cloud_unconfigured", "message": str(exc)},
        ) from exc


def get_bob_cloud_client_for_request(request: Request) -> BobCloudClient | None:
    if _local_auth_enabled() and _bearer_token(request):
        return None
    try:
        return get_bob_cloud_client()
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        if _local_auth_enabled() and detail.get("code") == "bob_cloud_unconfigured":
            return None
        raise


def _copy_set_cookie(source: httpx.Response, target: Response) -> None:
    for value in source.headers.get_list("set-cookie"):
        target.headers.append("set-cookie", value)


def _response_payload(source: httpx.Response) -> dict:
    if source.status_code == status.HTTP_204_NO_CONTENT or not source.content:
        return {}
    return source.json()


async def _proxy_bob_cloud(
    call: Callable[[], Awaitable[httpx.Response]],
    response: Response,
) -> dict:
    try:
        bob_cloud_response = await call()
    except BobCloudResponseError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "bob_cloud_unavailable", "message": str(exc)},
        ) from exc

    _copy_set_cookie(bob_cloud_response, response)
    return _response_payload(bob_cloud_response)


@router.get("/session")
async def get_session(
    request: Request,
    response: Response,
    bob_cloud_client: BobCloudClient | None = Depends(get_bob_cloud_client_for_request),
) -> dict:
    local_session = await _local_session(request)
    if local_session is not None:
        return local_session
    if bob_cloud_client is None:
        return {"authenticated": False, "source": "local-dev"}
    return await _proxy_bob_cloud(
        lambda: bob_cloud_client.get_session_response(forward_headers=request.headers),
        response,
    )


@router.post("/refresh")
async def refresh_session(
    request: Request,
    response: Response,
    bob_cloud_client: BobCloudClient | None = Depends(get_bob_cloud_client_for_request),
) -> dict:
    if bob_cloud_client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bob Cloud session unavailable")
    return await _proxy_bob_cloud(
        lambda: bob_cloud_client.refresh_session_response(forward_headers=request.headers),
        response,
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    bob_cloud_client: BobCloudClient | None = Depends(get_bob_cloud_client_for_request),
) -> dict:
    if bob_cloud_client is None:
        return {"authenticated": False, "source": "local-dev"}
    return await _proxy_bob_cloud(
        lambda: bob_cloud_client.logout_response(forward_headers=request.headers),
        response,
    )
