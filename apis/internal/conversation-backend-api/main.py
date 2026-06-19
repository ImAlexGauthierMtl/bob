"""Conversation Backend API. Port: 9012."""

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


settings = get_settings("conversation-backend")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


def create_internal_session_signer() -> InternalSessionContextSigner:
    environment = os.environ.get("ENV", os.environ.get("ENVIRONMENT", settings.environment)).lower()
    secret = os.environ.get("INTERNAL_SESSION_SECRET", "")
    if not secret and environment in {"development", "dev", "test", "ci"}:
        secret = "dev-internal-session-secret-not-for-production"
    if not secret:
        raise RuntimeError("INTERNAL_SESSION_SECRET is required for conversation-backend" + "-api")
    return InternalSessionContextSigner(
        secret,
        kid=os.environ.get("INTERNAL_SESSION_KID", "internal-session-dev"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.infrastructure.database import init as db_init
    from app.infrastructure.persistence.models import conversation  # noqa: F401

    db_init("conversation-backend")
    if hasattr(event_bus, "start_listening"):
        await event_bus.start_listening()
    logger.info("conversation_backend_started", port=9012)
    yield
    if hasattr(event_bus, "close"):
        await event_bus.close()


app = FastAPI(title="Conversation Backend API", version="0.1.0", lifespan=lifespan)
setup_cors(app, "conversation-backend")
app.add_middleware(RequestLoggingMiddleware)
app.middleware("http")(InternalSessionContextMiddleware(create_internal_session_signer()))
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.conversation_routes import router as conversation_router

app.include_router(conversation_router, tags=["conversation"])
