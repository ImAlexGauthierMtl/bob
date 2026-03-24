import os
"""AI Agent B4F API — Business logic layer for Bob, Client Map, Capabilities, Training.

Delegates all CRUD to agent~backend-api. Keeps LLM/agent logic, capability resolution,
behavioral analysis, and Bob orchestration. Port: 8003
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router

settings = get_settings("ai-agent")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ai_agent_b4f_api_started", port=settings.api_port)
    yield
    logger.info("ai_agent_b4f_api_shutdown")


api_prefix = os.environ.get("API_ROUTE_PREFIX", "")
root_path = f"/api/v1/{api_prefix}" if api_prefix else ""
app = FastAPI(root_path=root_path, 
    title="AI Agent B4F API",
    description="Business logic for Bob, Client Map 360°, Capabilities, Training — Croo Digital Experience",
    version="2.0.0",
    lifespan=lifespan,
)

setup_cors(app, "ai-agent")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])
if api_prefix:
    app.include_router(monitoring_router, prefix=f"/api/v1/{api_prefix}", tags=["monitoring"])

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
