"""Auth B4F API — authentication, authorization, JWT management.

B4F layer — business logic only, delegates CRUD to user~backend-api.
Port: 8001
"""
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router

settings = get_settings("auth")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)

app = FastAPI(
    title="Auth B4F API",
    description="Authentication & Authorization — Croo Digital Experience",
    version="1.0.0",
)

setup_cors(app, "auth")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.auth_routes import router as auth_router
from app.presentation.routes.user_routes import router as user_router
from app.presentation.routes.tenant_routes import router as tenant_router
from app.presentation.routes.role_routes import router as role_router
app.include_router(auth_router, tags=["auth"])
app.include_router(user_router, tags=["users"])
app.include_router(tenant_router, tags=["tenants"])
app.include_router(role_router, tags=["roles"])
