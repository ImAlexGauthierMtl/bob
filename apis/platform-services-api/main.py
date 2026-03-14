"""Platform Services API — Workflows, Usage Billing, Enrichment.

Microservice extracted from the monolith — Phase 5.
Port: 8005
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.database import Base, create_db_engine

settings = get_settings("platform-services")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.entities import workflow, workflow_execution, usage_transaction, enrichment_run  # noqa: F401
    engine = create_db_engine("platform-services")
    Base.metadata.create_all(bind=engine)
    logger.info("platform_services_api_started", port=settings.api_port)
    yield
    logger.info("platform_services_api_shutdown")

app = FastAPI(title="Platform Services API", description="Workflows, Usage, Enrichment — Croo", version="1.0.0", lifespan=lifespan)
setup_cors(app, "platform-services")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.workflow_routes import router as workflow_router
from app.presentation.routes.usage_routes import router as usage_router
from app.presentation.routes.enrichment_routes import router as enrichment_router

app.include_router(workflow_router, tags=["workflows"])
app.include_router(usage_router, tags=["usage"])
app.include_router(enrichment_router, tags=["enrichment"])
