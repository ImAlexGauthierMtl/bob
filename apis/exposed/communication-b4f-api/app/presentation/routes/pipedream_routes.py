"""Pipedream B4F routes delegated to email-backend-api provider operations."""

from fastapi import APIRouter, Request

from app.infrastructure.clients.provider_proxy import proxy_provider_request


router = APIRouter(prefix="/pipedream")


@router.api_route("", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_pipedream_root(request: Request):
    return await proxy_provider_request("pipedream", "", request)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_pipedream(path: str, request: Request):
    return await proxy_provider_request("pipedream", path, request)
