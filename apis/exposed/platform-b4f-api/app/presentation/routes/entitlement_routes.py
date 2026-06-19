"""Bob Cloud entitlement routes exposed through Platform B4F."""

from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
import httpx
from pydantic import BaseModel

from shared.services import (
    BobCloudClient,
    BobCloudModeError,
    BobCloudResponseError,
    create_bob_cloud_client_from_env,
)

router = APIRouter(prefix="/api/platform/v1")


class CapabilityCheckRequest(BaseModel):
    capability: str


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


@router.get("/entitlements/me")
async def get_my_entitlements(
    request: Request,
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict[str, Any]:
    return await _call_bob_cloud(
        lambda: bob_cloud_client.get_entitlements(forward_headers=request.headers)
    )


@router.get("/entitlements/check")
async def check_entitlement_query(
    request: Request,
    capability: str = Query(..., min_length=3),
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict[str, Any]:
    return await _call_bob_cloud(
        lambda: bob_cloud_client.check_capability(
            capability,
            forward_headers=request.headers,
        )
    )


@router.post("/entitlements/check")
async def check_entitlement(
    payload: CapabilityCheckRequest,
    request: Request,
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict[str, Any]:
    return await _call_bob_cloud(
        lambda: bob_cloud_client.check_capability(
            payload.capability,
            forward_headers=request.headers,
        )
    )
