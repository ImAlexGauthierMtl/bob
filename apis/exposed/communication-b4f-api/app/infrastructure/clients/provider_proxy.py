"""Thin B4F proxy for provider operations owned by email-backend-api."""

from typing import Any, Optional

from fastapi import Request, Response
from shared.services import create_service_client


_client = create_service_client("email~backend-api", timeout=60.0, max_retries=1)


async def proxy_provider_request(provider: str, path: str, request: Request) -> Response:
    """Forward a public B4F provider request to the internal provider backend route."""
    backend_path = f"/api/v1/provider/{provider}"
    if path:
        backend_path = f"{backend_path}/{path}"

    json_body: Optional[Any] = None
    if request.method in {"POST", "PUT", "PATCH"}:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.body()
            if body:
                json_body = await request.json()

    query_string = request.scope.get("query_string", b"").decode()
    proxied_path = f"{backend_path}?{query_string}" if query_string else backend_path
    method = request.method.upper()
    if method == "GET":
        response = await _client.get(proxied_path, forward_headers=request.headers)
    elif method == "POST":
        response = await _client.post(proxied_path, json=json_body, forward_headers=request.headers)
    elif method == "PUT":
        response = await _client.put(proxied_path, json=json_body, forward_headers=request.headers)
    elif method == "PATCH":
        response = await _client.patch(proxied_path, json=json_body, forward_headers=request.headers)
    elif method == "DELETE":
        response = await _client.delete(proxied_path, forward_headers=request.headers)
    else:
        return Response(status_code=405)

    headers = {}
    for key in ("content-type", "location", "content-disposition"):
        if key in response.headers:
            headers[key] = response.headers[key]
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=headers,
    )
