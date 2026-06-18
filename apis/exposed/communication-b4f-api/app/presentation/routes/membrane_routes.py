"""Membrane B4F routes delegated to email-backend-api provider operations."""

from fastapi import APIRouter, Request

from app.infrastructure.clients.provider_proxy import proxy_provider_request


router = APIRouter(prefix="/membrane")


@router.api_route("", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_membrane_root(request: Request):
    return await proxy_provider_request("membrane", "", request)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_membrane(path: str, request: Request):
    return await proxy_provider_request("membrane", path, request)
