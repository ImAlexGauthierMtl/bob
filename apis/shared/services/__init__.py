"""HTTP client for inter-service communication."""

from typing import Optional, Dict, Any
import httpx
from ..infrastructure.logging import get_logger

logger = get_logger(__name__)


class HTTPClient:
    """Async HTTP client for service-to-service calls.

    Usage:
        client = HTTPClient(base_url="http://crm-backend-api:8002")
        response = await client.get("/api/v1/contacts", headers=auth_headers)
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Any] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                params=params,
            )
            logger.info(
                "http_client_request",
                method=method,
                url=url,
                status=response.status_code,
            )
            return response

    async def get(self, path: str, headers: Optional[Dict] = None, params: Optional[Dict] = None) -> httpx.Response:
        return await self._request("GET", path, headers=headers, params=params)

    async def post(self, path: str, json: Any = None, headers: Optional[Dict] = None) -> httpx.Response:
        return await self._request("POST", path, headers=headers, json=json)

    async def put(self, path: str, json: Any = None, headers: Optional[Dict] = None) -> httpx.Response:
        return await self._request("PUT", path, headers=headers, json=json)

    async def patch(self, path: str, json: Any = None, headers: Optional[Dict] = None) -> httpx.Response:
        return await self._request("PATCH", path, headers=headers, json=json)

    async def delete(self, path: str, headers: Optional[Dict] = None) -> httpx.Response:
        return await self._request("DELETE", path, headers=headers)
