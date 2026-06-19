"""Agent Control B4F API - bounded control surface for Bob."""

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from shared.config import get_settings
from shared.infrastructure import (
    RequestLoggingMiddleware,
    configure_logging,
    get_logger,
    monitoring_router,
    setup_cors,
)

from app.middleware.auth import require_agent_control_permission
from app.presentation.routes.agent_control_routes import router as agent_control_router
from app.presentation.routes.bcc_routes import router as bcc_router
from app.presentation.routes.client_map_routes import router as client_map_router
from app.presentation.routes.training_routes import router as training_router


settings = get_settings("agent-control")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("agent_control_b4f_api_started", port=settings.api_port)
    yield
    logger.info("agent_control_b4f_api_shutdown")


def create_app() -> FastAPI:
    application = FastAPI(
        title="Agent Control B4F API",
        description="Bounded BCC, Training and Client Map control surface - Croo Digital Experience",
        version="2.0.0",
        lifespan=lifespan,
    )

    setup_cors(application, "agent-control")
    application.add_middleware(RequestLoggingMiddleware)
    application.include_router(monitoring_router, tags=["monitoring"])

    api_prefix = os.environ.get("API_ROUTE_PREFIX", "")
    if api_prefix:
        application.include_router(
            monitoring_router,
            prefix=f"/api/v1/{api_prefix}",
            tags=["monitoring"],
        )

    permission_guard = [Depends(require_agent_control_permission)]
    application.include_router(agent_control_router, tags=["agent-control"], dependencies=permission_guard)
    application.include_router(bcc_router, tags=["bcc"], dependencies=permission_guard)
    application.include_router(client_map_router, tags=["client-map"], dependencies=permission_guard)
    application.include_router(training_router, tags=["training"], dependencies=permission_guard)
    return application


app = create_app()
