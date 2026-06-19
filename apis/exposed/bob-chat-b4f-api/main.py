"""Bob Chat B4F API — conversation facade for Bob."""

import os

from fastapi import FastAPI

from shared.config import get_settings
from shared.infrastructure import (
    RequestLoggingMiddleware,
    configure_logging,
    get_logger,
    monitoring_router,
    setup_cors,
)

settings = get_settings("bob-chat")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)

app = FastAPI(
    title="Bob Chat B4F API",
    description="Bob Chat facade — Croo Digital Experience",
    version="0.1.0",
)

setup_cors(app, "bob-chat")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])
_api_prefix = os.environ.get("API_ROUTE_PREFIX", "")
if _api_prefix:
    app.include_router(monitoring_router, prefix=f"/api/v1/{_api_prefix}", tags=["monitoring"])

from app.presentation.routes.bob_chat_routes import router as bob_chat_router

app.include_router(bob_chat_router, tags=["bob-chat"])
app.include_router(bob_chat_router, prefix="/api/bob-chat/v1", tags=["bob-chat-public"])
