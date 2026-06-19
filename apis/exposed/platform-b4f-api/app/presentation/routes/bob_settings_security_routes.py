"""Security/RBAC settings delegated to Bob Cloud."""

from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
import httpx

from shared.services import (
    BobCloudClient,
    BobCloudModeError,
    BobCloudResponseError,
    create_bob_cloud_client_from_env,
)

router = APIRouter(prefix="/security")


def get_bob_cloud_client() -> BobCloudClient:
    try:
        return create_bob_cloud_client_from_env()
    except BobCloudModeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "bob_cloud_unconfigured", "message": str(exc)},
        ) from exc


async def _call_bob_cloud(call: Callable[[], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
    try:
        return await call()
    except BobCloudResponseError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "bob_cloud_unavailable", "message": str(exc)},
        ) from exc


@router.get("/users")
async def list_users(
    request: Request,
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict[str, Any]:
    return await _call_bob_cloud(
        lambda: bob_cloud_client.list_users(forward_headers=request.headers)
    )


@router.get("/tenants")
async def list_tenants(
    request: Request,
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict[str, Any]:
    return await _call_bob_cloud(
        lambda: bob_cloud_client.list_tenants(forward_headers=request.headers)
    )


@router.patch("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    payload: dict[str, Any],
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict[str, Any]:
    return await _call_bob_cloud(
        lambda: bob_cloud_client.update_tenant(
            tenant_id,
            payload,
            idempotency_key=idempotency_key,
            forward_headers=request.headers,
        )
    )


@router.get("/licenses")
async def list_licenses(
    request: Request,
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict[str, Any]:
    return await _call_bob_cloud(
        lambda: bob_cloud_client.list_licenses(forward_headers=request.headers)
    )


@router.patch("/licenses/{capability}")
async def update_license(
    capability: str,
    payload: dict[str, Any],
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict[str, Any]:
    return await _call_bob_cloud(
        lambda: bob_cloud_client.update_license(
            capability,
            payload,
            idempotency_key=idempotency_key,
            forward_headers=request.headers,
        )
    )


@router.post("/invitations")
async def create_invitation(
    payload: dict[str, Any],
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict[str, Any]:
    return await _call_bob_cloud(
        lambda: bob_cloud_client.create_invitation(
            payload,
            idempotency_key=idempotency_key,
            forward_headers=request.headers,
        )
    )


@router.get("/roles")
async def list_roles(
    request: Request,
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict[str, Any]:
    return await _call_bob_cloud(
        lambda: bob_cloud_client.list_roles(forward_headers=request.headers)
    )


@router.get("/memberships")
async def list_memberships(
    request: Request,
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict[str, Any]:
    return await _call_bob_cloud(
        lambda: bob_cloud_client.list_memberships(forward_headers=request.headers)
    )


@router.patch("/memberships/{membership_id}")
async def update_membership(
    membership_id: str,
    payload: dict[str, Any],
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict[str, Any]:
    return await _call_bob_cloud(
        lambda: bob_cloud_client.update_membership(
            membership_id,
            payload,
            idempotency_key=idempotency_key,
            forward_headers=request.headers,
        )
    )
