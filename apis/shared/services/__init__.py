"""HTTP client for inter-service communication with retry, circuit breaker, and header forwarding."""

from typing import Optional, Dict, Any, List
from enum import Enum
import asyncio
import os
import time

import httpx

from ..infrastructure.logging import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Simple circuit breaker to prevent cascading failures."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._state = CircuitState.CLOSED

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning("circuit_breaker_opened", failures=self._failure_count)

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN


FORWARDED_HEADERS = ["authorization", "x-tenant-id", "x-request-id", "x-correlation-id"]


class HTTPClient:
    """Async HTTP client for service-to-service calls with retry and circuit breaker.

    Usage:
        client = HTTPClient(base_url="http://user-backend-api:9001")
        response = await client.get("/api/v1/users", forward_headers=request.headers)
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 0.5,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    def _build_headers(
        self,
        headers: Optional[Dict[str, str]] = None,
        forward_headers: Optional[Any] = None,
    ) -> Dict[str, str]:
        """Build request headers, forwarding auth/tenant headers from the incoming request."""
        result: Dict[str, str] = {}
        if forward_headers:
            mapping = forward_headers if isinstance(forward_headers, dict) else dict(forward_headers)
            for key, value in mapping.items():
                if key.lower() in FORWARDED_HEADERS:
                    result[key] = value
        if headers:
            result.update(headers)
        return result

    async def _request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        forward_headers: Optional[Any] = None,
        json: Optional[Any] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        if self.circuit_breaker.is_open:
            raise httpx.HTTPStatusError(
                "Circuit breaker is open",
                request=httpx.Request(method, f"{self.base_url}{path}"),
                response=httpx.Response(503),
            )

        url = f"{self.base_url}{path}"
        merged_headers = self._build_headers(headers, forward_headers)
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=merged_headers,
                        json=json,
                        params=params,
                    )
                self.circuit_breaker.record_success()
                logger.info("http_request", method=method, url=url, status=response.status_code, attempt=attempt)
                return response
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                last_exc = e
                self.circuit_breaker.record_failure()
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))
                    logger.warning("http_retry", method=method, url=url, attempt=attempt, delay=delay, error=str(e))
                    await asyncio.sleep(delay)

        logger.error("http_request_failed", method=method, url=url, attempts=self.max_retries, error=str(last_exc))
        raise last_exc  # type: ignore[misc]

    async def get(self, path: str, headers: Optional[Dict] = None, params: Optional[Dict] = None, forward_headers: Optional[Any] = None) -> httpx.Response:
        return await self._request("GET", path, headers=headers, params=params, forward_headers=forward_headers)

    async def post(self, path: str, json: Any = None, headers: Optional[Dict] = None, forward_headers: Optional[Any] = None) -> httpx.Response:
        return await self._request("POST", path, headers=headers, json=json, forward_headers=forward_headers)

    async def put(self, path: str, json: Any = None, headers: Optional[Dict] = None, forward_headers: Optional[Any] = None) -> httpx.Response:
        return await self._request("PUT", path, headers=headers, json=json, forward_headers=forward_headers)

    async def patch(self, path: str, json: Any = None, headers: Optional[Dict] = None, forward_headers: Optional[Any] = None) -> httpx.Response:
        return await self._request("PATCH", path, headers=headers, json=json, forward_headers=forward_headers)

    async def delete(self, path: str, headers: Optional[Dict] = None, forward_headers: Optional[Any] = None) -> httpx.Response:
        return await self._request("DELETE", path, headers=headers, forward_headers=forward_headers)


_SERVICE_URL_MAP: Dict[str, str] = {
    "user~backend-api": "USER_BACKEND_API_URL",
    "contact~backend-api": "CONTACT_BACKEND_API_URL",
    "org~backend-api": "ORG_BACKEND_API_URL",
    "opportunity~backend-api": "OPPORTUNITY_BACKEND_API_URL",
    "activity~backend-api": "ACTIVITY_BACKEND_API_URL",
    "product~backend-api": "PRODUCT_BACKEND_API_URL",
    "email~backend-api": "EMAIL_BACKEND_API_URL",
    "agent~backend-api": "AGENT_BACKEND_API_URL",
    "workflow~backend-api": "WORKFLOW_BACKEND_API_URL",
    "kb~backend-api": "KB_BACKEND_API_URL",
    "usage~backend-api": "USAGE_BACKEND_API_URL",
    "auth~b4f-api": "AUTH_B4F_API_URL",
    "crm~b4f-api": "CRM_B4F_API_URL",
    "communication~b4f-api": "COMMUNICATION_B4F_API_URL",
    "ai-agent~b4f-api": "AI_AGENT_B4F_API_URL",
    "platform~b4f-api": "PLATFORM_B4F_API_URL",
    "kb~b4f-api": "KB_B4F_API_URL",
}

_DEFAULT_PORTS: Dict[str, int] = {
    "user~backend-api": 9001,
    "contact~backend-api": 9002,
    "org~backend-api": 9003,
    "opportunity~backend-api": 9004,
    "activity~backend-api": 9005,
    "product~backend-api": 9006,
    "email~backend-api": 9007,
    "agent~backend-api": 9008,
    "workflow~backend-api": 9009,
    "kb~backend-api": 9010,
    "usage~backend-api": 9011,
    "auth~b4f-api": 8001,
    "crm~b4f-api": 8002,
    "communication~b4f-api": 8004,
    "ai-agent~b4f-api": 8003,
    "platform~b4f-api": 8005,
    "kb~b4f-api": 8006,
}


def get_service_url(service_name: str) -> str:
    """Resolve a service URL from environment variables with sensible defaults.

    Checks the env var mapped to the service name (e.g. USER_BACKEND_API_URL),
    falling back to http://<docker-compose-name>:<default-port>.
    """
    env_var = _SERVICE_URL_MAP.get(service_name)
    if env_var:
        url = os.environ.get(env_var)
        if url:
            return url.rstrip("/")

    docker_name = service_name.replace("~", "-")
    port = _DEFAULT_PORTS.get(service_name, 8000)
    return f"http://{docker_name}:{port}"


def create_service_client(service_name: str, **kwargs: Any) -> HTTPClient:
    """Create an HTTPClient configured for a specific backend service."""
    url = get_service_url(service_name)
    return HTTPClient(base_url=url, **kwargs)
