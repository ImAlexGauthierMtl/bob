"""Organization Backend API — CRUD for organizations and departments. Port: 9003."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.database import Base
from shared.event_bus import event_bus

settings = get_settings("org-backend")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.entities import organization, department  # noqa: F401
    from app.infrastructure.database import init as db_init, get_engine
    db_init("org-backend")
    Base.metadata.create_all(bind=get_engine())
    if hasattr(event_bus, 'start_listening'):
        await event_bus.start_listening()
    logger.info("org_backend_started", port=9003)
    yield
    if hasattr(event_bus, 'close'):
        await event_bus.close()


app = FastAPI(title="Organization Backend API", version="1.0.0", lifespan=lifespan)
setup_cors(app, "org-backend")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.organization_routes import router as org_router
from app.presentation.routes.department_routes import router as dept_router
app.include_router(org_router, tags=["organizations"])
app.include_router(dept_router, tags=["departments"])
