"""User Backend API — CRUD for users, tenants, roles, permissions.

Pure storage layer — no business logic. Port: 9001.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.database import Base
from shared.event_bus import event_bus

settings = get_settings("user-backend")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.entities import user, tenant, role  # noqa: F401
    from app.infrastructure.database import init as db_init, get_engine, get_session_factory
    db_init("user-backend")
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("database_tables_created")

    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        from app.infrastructure.seed import run_seed
        from app.infrastructure.seed_roles import seed_roles, backfill_user_roles
        run_seed(db)
        admin = db.query(user.User).filter(user.User.email == settings.admin_email).first()
        if admin:
            seed_roles(db, tenant_id=admin.tenant_id)
            backfill_user_roles(db, tenant_id=admin.tenant_id)
    finally:
        db.close()

    if hasattr(event_bus, 'start_listening'):
        await event_bus.start_listening()
    logger.info("user_backend_api_started", port=settings.api_port)
    yield
    if hasattr(event_bus, 'close'):
        await event_bus.close()
    logger.info("user_backend_api_shutdown")


app = FastAPI(title="User Backend API", version="1.0.0", lifespan=lifespan)
setup_cors(app, "user-backend")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.user_routes import router as user_router
from app.presentation.routes.tenant_routes import router as tenant_router
from app.presentation.routes.role_routes import router as role_router
app.include_router(user_router, tags=["users"])
app.include_router(tenant_router, tags=["tenants"])
app.include_router(role_router, tags=["roles"])
