"""Factory to create a standard backend-api FastAPI application."""

from typing import Optional, List, Callable
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ...config import get_settings
from ...infrastructure.logging import configure_logging, get_logger
from ...infrastructure.monitoring import router as monitoring_router
from ...infrastructure.auth_middleware import JWTAuthMiddleware

logger = get_logger(__name__)


def create_backend_app(
    service_name: str,
    title: Optional[str] = None,
    version: str = "1.0.0",
    api_prefix: str = "/api/v1",
    extra_public_paths: Optional[List[str]] = None,
    on_startup: Optional[List[Callable]] = None,
    on_shutdown: Optional[List[Callable]] = None,
) -> FastAPI:
    """Create a configured FastAPI app for a backend-api service.

    Includes: CORS, JWT middleware, health routes, structured logging.
    """
    settings = get_settings(service_name)
    configure_logging(
        log_level=settings.log_level,
        log_format="console" if settings.environment in ("development", "dev") else "json",
    )

    display_title = title or f"Croo {service_name}"
    app = FastAPI(title=display_title, version=version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    jwt_middleware = JWTAuthMiddleware(extra_public_paths=extra_public_paths)
    app.middleware("http")(jwt_middleware)

    app.include_router(monitoring_router)

    if on_startup:
        for fn in on_startup:
            app.add_event_handler("startup", fn)
    if on_shutdown:
        for fn in on_shutdown:
            app.add_event_handler("shutdown", fn)

    logger.info("backend_app_created", service=service_name, port=settings.api_port)
    return app
