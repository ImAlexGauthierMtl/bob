import os
"""KB B4F API — business logic + aggregation, delegates CRUD to kb~backend-api. Port: 8006."""
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router

settings = get_settings("kb")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)

app = FastAPI( title="KB B4F API", version="1.0.0")
setup_cors(app, "kb")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])
_api_prefix = os.environ.get("API_ROUTE_PREFIX", "")
if _api_prefix:
    app.include_router(monitoring_router, prefix=f"/api/v1/{_api_prefix}", tags=["monitoring"])

from app.presentation.routes.kb_routes import router as kb_router
app.include_router(kb_router, tags=["knowledge-base"])
