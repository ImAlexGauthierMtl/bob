import os
"""Communication B4F API — MS365 OAuth, Sync Orchestration, AI, Webhooks.

Business-for-Frontend layer — no direct DB access. Port: 8004.
Delegates CRUD to email~backend-api via HTTP.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router

settings = get_settings("communication")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("communication_b4f_started", port=settings.api_port)
    yield
    logger.info("communication_b4f_shutdown")


api_prefix = os.environ.get("API_ROUTE_PREFIX", "")
root_path = f"/api/v1/{api_prefix}" if api_prefix else ""
app = FastAPI(root_path=root_path, 
    title="Communication B4F API",
    description="MS365 OAuth, Sync, AI Smart Labels, Webhooks — Croo",
    version="1.0.0",
    lifespan=lifespan,
)
setup_cors(app, "communication")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])
if api_prefix:
    app.include_router(monitoring_router, prefix=f"/api/v1/{api_prefix}", tags=["monitoring"])

from app.presentation.routes.ms365_routes import router as ms365_router
from app.presentation.routes.smart_label_routes import router as smart_label_router
from app.presentation.routes.webhook_routes import router as webhook_router

app.include_router(ms365_router, tags=["ms365"])
app.include_router(smart_label_router, tags=["smart-labels"])
app.include_router(webhook_router, tags=["webhooks"])
