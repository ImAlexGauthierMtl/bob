"""Bob Cloud-backed auth routes.

These routes run in parallel with the legacy `/auth/*` JWT flow until the
frontend cutover is explicit.
"""

from typing import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
import httpx

from shared.services import (
    BobCloudClient,
    BobCloudModeError,
    BobCloudResponseError,
    create_bob_cloud_client_from_env,
)

router = APIRouter(prefix="/api/auth/v1")


def get_bob_cloud_client() -> BobCloudClient:
    try:
        return create_bob_cloud_client_from_env()
    except BobCloudModeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "bob_cloud_unconfigured", "message": str(exc)},
        ) from exc


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
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict:
    return await _proxy_bob_cloud(
        lambda: bob_cloud_client.get_session_response(forward_headers=request.headers),
        response,
    )


@router.post("/refresh")
async def refresh_session(
    request: Request,
    response: Response,
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict:
    return await _proxy_bob_cloud(
        lambda: bob_cloud_client.refresh_session_response(forward_headers=request.headers),
        response,
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    bob_cloud_client: BobCloudClient = Depends(get_bob_cloud_client),
) -> dict:
    return await _proxy_bob_cloud(
        lambda: bob_cloud_client.logout_response(forward_headers=request.headers),
        response,
    )
