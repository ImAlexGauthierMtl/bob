"""CORS setup and request logging middleware."""

import os
import re
import time
from typing import Optional
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .logging import bind_trace_context, clear_trace_context, get_logger
from ..config import get_settings

logger = get_logger(__name__)
TRACEPARENT_RE = re.compile(
    r"^[0-9a-f]{2}-([0-9a-f]{32})-[0-9a-f]{16}-[0-9a-f]{2}$"
)


def setup_cors(app: FastAPI, api_name: Optional[str] = None) -> None:
    """Configure CORS middleware using shared settings.

    In non-development environments, only the explicit `cors_origins` list
    from settings is honored. In development, the `INGRESS_URL` env var and
    a small list of well-known local dev-server origins are auto-added for
    convenience so engineers don't have to tweak the `.env` on every setup.
    """
    settings = get_settings(api_name)
    origins = list(settings.cors_origins)

    is_dev = settings.environment.lower() in ("development", "dev", "local")
    if is_dev:
        # Auto-add the frontend dev-server origin if INGRESS_URL is set
        ingress = os.environ.get("INGRESS_URL", "")
        if ingress and ingress not in origins:
            origins.append(ingress)
        # Also add common Angular/Vite dev origins if not present
        for dev_origin in ("http://localhost:4200", "http://localhost:4300", "http://localhost:24200"):
            if dev_origin not in origins:
                origins.append(dev_origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        trace_id, traceparent, request_id = _trace_context_from_request(request)
        bind_trace_context(trace_id, traceparent, request_id)
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "http_request_error",
                method=request.method,
                path=str(request.url.path),
                duration_ms=duration_ms,
                client=request.client.host if request.client else None,
            )
            raise
        else:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            response.headers["traceparent"] = traceparent
            response.headers["x-request-id"] = request_id
            logger.info(
                "http_request",
                method=request.method,
                path=str(request.url.path),
                status=response.status_code,
                duration_ms=duration_ms,
                client=request.client.host if request.client else None,
            )
            return response
        finally:
            clear_trace_context()


def _trace_context_from_request(request: Request) -> tuple[str, str, str]:
    traceparent = request.headers.get("traceparent", "").strip().lower()
    match = TRACEPARENT_RE.match(traceparent)
    if match and match.group(1) != "0" * 32:
        trace_id = match.group(1)
    else:
        trace_id = uuid.uuid4().hex
        traceparent = f"00-{trace_id}-{uuid.uuid4().hex[:16]}-01"
    request_id = request.headers.get("x-request-id") or trace_id
    return trace_id, traceparent, request_id
