"""CORS setup and request logging middleware."""

import os
import time
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .logging import get_logger
from ..config import get_settings

logger = get_logger(__name__)


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
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "http_request",
            method=request.method,
            path=str(request.url.path),
            status=response.status_code,
            duration_ms=duration_ms,
            client=request.client.host if request.client else None,
        )
        return response
