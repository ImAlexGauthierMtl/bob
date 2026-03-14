"""Auth API — authentication, users, tenants, RBAC.

Microservice extracted from the monolith — Phase 1.
Port: 8001
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.database import Base, create_db_engine, create_session_factory

settings = get_settings("auth")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    # Import entities to register with Base.metadata
    from app.domain.entities import user, tenant, role  # noqa: F401

    engine = create_db_engine("auth")
    Base.metadata.create_all(bind=engine)
    logger.info("database_tables_created")

    # Seed admin + roles
    SessionLocal = create_session_factory("auth")
    db = SessionLocal()
    try:
        from app.infrastructure.seed import run_seed
        from app.infrastructure.seed_roles import seed_roles
        run_seed(db)
        admin = db.query(user.User).filter(
            user.User.email == settings.admin_email
        ).first()
        if admin:
            seed_roles(db, tenant_id=admin.tenant_id)
    finally:
        db.close()

    logger.info("auth_api_started", port=settings.api_port)
    yield
    logger.info("auth_api_shutdown")


app = FastAPI(
    title="Auth API",
    description="Authentication, Users, Tenants, RBAC — Croo Digital Experience",
    version="1.0.0",
    lifespan=lifespan,
)

setup_cors(app, "auth")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

# Import and include routers
from app.presentation.routes.auth_routes import router as auth_router
from app.presentation.routes.user_routes import router as user_router
from app.presentation.routes.tenant_routes import router as tenant_router
from app.presentation.routes.role_routes import router as role_router

app.include_router(auth_router, tags=["auth"])
app.include_router(user_router, tags=["users"])
app.include_router(tenant_router, tags=["tenants"])
app.include_router(role_router, tags=["roles"])
