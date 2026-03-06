# Template: Middleware CORS + Logging structuré + Error Handling

> Recette pour le middleware de base : CORS, logging des requêtes, et gestion d'erreurs.
> **Zéro décision** : suivre exactement ce pattern.

## Fichiers à créer (2 fichiers)

### 1. `shared/infrastructure/middleware.py`

```python
"""FastAPI middleware for CORS, error handling, and request logging."""

import time
import uuid
from typing import Callable
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from ..infrastructure.logging import get_logger
from ..config.settings import get_settings

logger = get_logger(__name__)


def setup_cors(app: FastAPI, api_name: str | None = None) -> None:
    """Setup CORS middleware."""
    settings = get_settings(api_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.time()

        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            request_id=request_id,
        )

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time=process_time,
                request_id=request_id,
            )

            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                process_time=process_time,
                request_id=request_id,
            )
            raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for global error handling."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception(
                "unhandled_exception",
                error=str(e),
                request_id=getattr(request.state, "request_id", None),
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
```

### 2. `shared/infrastructure/logging.py`

```python
"""Structured logging configuration with structlog."""

import logging
import sys
from typing import Any
import structlog
from structlog.stdlib import LoggerFactory


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure structured logging with structlog."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Get a structured logger instance."""
    return structlog.get_logger(name)
```

## Règles NON-NÉGOCIABLES

1. `structlog` — jamais `print()` ou `logging.getLogger()` direct
2. UUID request_id sur chaque requête, ajouté au header `X-Request-ID`
3. Logging structuré avec méthode, path, status_code, process_time
4. JSON en production, ConsoleRenderer en dev
5. `ErrorHandlingMiddleware` attrape les exceptions non gérées
6. CORS configuré depuis les settings centralisées
