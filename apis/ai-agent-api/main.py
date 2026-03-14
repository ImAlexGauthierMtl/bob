"""AI Agent API — Bob's Control Center, Client Map 360°, Capabilities, Training.

Microservice extracted from the monolith — Phase 3.
Port: 8003
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.database import Base, create_db_engine

settings = get_settings("ai-agent")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.entities import bcc_entities, bob_settings, capability, client_map, training_models  # noqa: F401
    engine = create_db_engine("ai-agent")
    Base.metadata.create_all(bind=engine)
    logger.info("ai_agent_database_tables_created")
    logger.info("ai_agent_api_started", port=settings.api_port)
    yield
    logger.info("ai_agent_api_shutdown")


app = FastAPI(
    title="AI Agent API",
    description="Bob's Control Center, Client Map 360°, Capabilities, Training — Croo Digital Experience",
    version="1.0.0",
    lifespan=lifespan,
)

setup_cors(app, "ai-agent")
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
