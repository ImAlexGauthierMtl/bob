"""Agent Backend API — pure CRUD for BCC, Bob Settings, Client Map, Capabilities, Training.

Storage layer for Bob Agent Control domain data. Port: 9008.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.event_bus import event_bus

settings = get_settings("agent-backend")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.infrastructure.persistence.models import (  # noqa: F401
        bcc_entities, bob_settings, capability, client_map,
        training_models, department,
    )
    from app.infrastructure.database import init as db_init
    db_init("agent-backend")

    from app.infrastructure.seed_org import seed_default_organization
    from shared.database import create_session_factory
    SessionLocal = create_session_factory("agent-backend")
    db = SessionLocal()
    try:
        seed_default_organization(db)
    finally:
        db.close()

    if hasattr(event_bus, "start_listening"):
        await event_bus.start_listening()
    logger.info("agent_backend_api_started", port=settings.api_port)
    yield
    if hasattr(event_bus, "close"):
        await event_bus.close()
    logger.info("agent_backend_api_shutdown")


app = FastAPI(
    title="Agent Backend API",
    description="Pure CRUD for BCC, Bob Settings, Client Map 360°, Capabilities, Training — Croo Digital Experience",
    version="1.0.0",
    lifespan=lifespan,
)

setup_cors(app, "agent-backend")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.bcc_routes import router as bcc_router
from app.presentation.routes.bob_settings_routes import router as bob_settings_router
from app.presentation.routes.client_map_routes import router as client_map_router
from app.presentation.routes.capability_routes import router as capability_router
from app.presentation.routes.training_routes import router as training_router

app.include_router(bcc_router, tags=["bcc"])
app.include_router(bob_settings_router, tags=["bob-settings"])
app.include_router(client_map_router, tags=["client-map"])
app.include_router(capability_router, tags=["capabilities"])
app.include_router(training_router, tags=["training"])
