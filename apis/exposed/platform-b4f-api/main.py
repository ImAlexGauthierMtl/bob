import os
"""Platform B4F API — business logic + aggregation, delegates CRUD to backends. Port: 8005."""
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router

settings = get_settings("platform-services")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)

app = FastAPI( title="Platform B4F API", version="1.0.0")
setup_cors(app, "platform-services")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])
_api_prefix = os.environ.get("API_ROUTE_PREFIX", "")
if _api_prefix:
    app.include_router(monitoring_router, prefix=f"/api/v1/{_api_prefix}", tags=["monitoring"])

from app.presentation.routes.workflow_routes import router as workflow_router
from app.presentation.routes.usage_routes import router as usage_router
from app.presentation.routes.enrichment_routes import router as enrichment_router

app.include_router(workflow_router, tags=["workflows"])
app.include_router(usage_router, tags=["usage"])
app.include_router(enrichment_router, tags=["enrichment"])
