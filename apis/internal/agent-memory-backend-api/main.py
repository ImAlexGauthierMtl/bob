"""Agent Memory Backend API. Port: 9014."""

from __future__ import annotations

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI

from shared.config import get_settings
from shared.event_bus import event_bus
from shared.infrastructure import (
    InternalSessionContextMiddleware,
    InternalSessionContextSigner,
    RequestLoggingMiddleware,
    configure_logging,
    get_logger,
    monitoring_router,
    setup_cors,
)


settings = get_settings("agent-memory-backend")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


def create_internal_session_signer() -> InternalSessionContextSigner:
    environment = os.environ.get("ENV", os.environ.get("ENVIRONMENT", settings.environment)).lower()
    secret = os.environ.get("INTERNAL_SESSION_SECRET", "")
    if not secret and environment in {"development", "dev", "test", "ci"}:
        secret = "dev-internal-session-secret-not-for-production"
    if not secret:
        raise RuntimeError("INTERNAL_SESSION_SECRET is required for agent-memory-backend" + "-api")
    return InternalSessionContextSigner(
        secret,
        kid=os.environ.get("INTERNAL_SESSION_KID", "internal-session-dev"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.infrastructure.database import init as db_init
    from app.infrastructure.persistence.models import agent_memory  # noqa: F401

    db_init("agent-memory-backend")
    if hasattr(event_bus, "start_listening"):
        await event_bus.start_listening()
    logger.info("agent_memory_backend_started", port=9014)
    yield
    if hasattr(event_bus, "close"):
        await event_bus.close()


app = FastAPI(title="Agent Memory Backend API", version="0.1.0", lifespan=lifespan)
setup_cors(app, "agent-memory-backend")
app.add_middleware(RequestLoggingMiddleware)
app.middleware("http")(InternalSessionContextMiddleware(create_internal_session_signer()))
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.agent_memory_routes import router as agent_memory_router

app.include_router(agent_memory_router, tags=["agent-memory"])
