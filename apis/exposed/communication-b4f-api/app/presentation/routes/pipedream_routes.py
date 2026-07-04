"""Pipedream B4F routes delegated to email-backend-api provider operations."""

from fastapi import APIRouter, HTTPException, Request

from app.infrastructure.clients.email_client import membrane_crud_client
from app.infrastructure.clients.provider_proxy import proxy_provider_request


router = APIRouter(prefix="/pipedream")


@router.api_route("", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_pipedream_root(request: Request):
    return await proxy_provider_request("pipedream", "", request)


@router.delete("/local-connections/{connection_id}", status_code=204)
async def delete_local_pipedream_connection(connection_id: str, request: Request):
    removed = await membrane_crud_client.delete_connection(connection_id, forward_headers=request.headers)
    if not removed:
        raise HTTPException(status_code=404, detail="Connection not found")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_pipedream(path: str, request: Request):
    return await proxy_provider_request("pipedream", path, request)
