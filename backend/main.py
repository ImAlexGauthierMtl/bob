"""Main FastAPI application for Croo Digital Experience API."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

import structlog

logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    from app.infrastructure.database import engine, SessionLocal
    from app.domain.entities.base import Base
    # Import entities so they register with Base.metadata
    from app.domain.entities import user, organization, contact, opportunity, quote, activity, department, capability, bob_settings, tenant  # noqa: F401
    from app.domain.entities import workflow, workflow_execution  # noqa: F401
    from app.domain.entities import bcc_entities  # noqa: F401
    from app.domain.entities import ms365_connection, synced_email, synced_event  # noqa: F401
    from app.domain.entities import email_contact, smart_label  # noqa: F401
    from app.domain.entities import client_map as client_map_entity  # noqa: F401
    from app.domain.entities import training_models  # noqa: F401
    from app.domain.entities import role as role_entities  # noqa: F401
    from app.domain.entities import product as product_entity  # noqa: F401
    from app.domain.entities import opportunity_product as opp_product_entity  # noqa: F401
    from app.domain.entities import usage_transaction as usage_transaction_entity  # noqa: F401
    from app.infrastructure.seed import run_seed
    from app.infrastructure.seed_capabilities import seed_capabilities
    from app.infrastructure.seed_workflows import seed_workflows
    from app.infrastructure.seed_bcc import seed_bcc
    from app.infrastructure.seed_bcc_cognitive import seed_bcc_cognitive
    from app.infrastructure.seed_roles import seed_roles
    from app.infrastructure.seed_rate_cards import seed_rate_cards
    from app.infrastructure.seed_smart_labels import seed_smart_labels

    # Create tables (will be replaced by alembic upgrade in production)
    Base.metadata.create_all(bind=engine)
    logger.info("database_tables_created")

    # Seed admin + capabilities + workflows
    db = SessionLocal()
    try:
        run_seed(db)
        seed_capabilities(db)
        admin = db.query(user.User).filter(user.User.email == settings.admin_email).first()
        if admin:
            seed_workflows(db, tenant_id=admin.tenant_id)
            seed_bcc(db, tenant_id=admin.tenant_id)
            seed_bcc_cognitive(db, tenant_id=admin.tenant_id)
            seed_roles(db, tenant_id=admin.tenant_id)
            seed_smart_labels(db, tenant_id=admin.tenant_id)
        # Seed cognitive structure for all tenants
        from sqlalchemy import distinct
        all_tenants = [r[0] for r in db.query(distinct(user.User.tenant_id)).all()]
        for tid in all_tenants:
            seed_bcc_cognitive(db, tenant_id=tid)
            seed_smart_labels(db, tenant_id=tid)
        seed_rate_cards(db)
    finally:
        db.close()
    logger.info("api_started", environment=settings.environment)

    # Start MS365 background sync task (polling fallback)
    ms365_sync_task = None
    if settings.ms365_client_id:
        async def _ms365_polling_loop():
            """Background task — sync all active M365 connections."""
            while True:
                await asyncio.sleep(settings.ms365_sync_interval_seconds)
                try:
                    from app.application.services.ms365_sync_service import MS365SyncService
                    poll_db = SessionLocal()
                    try:
                        svc = MS365SyncService(poll_db)
                        await svc.sync_all_active_connections()
                    finally:
                        poll_db.close()
                except Exception as e:
                    logger.error("ms365_polling_error", error=str(e))

        ms365_sync_task = asyncio.create_task(_ms365_polling_loop())
        logger.info("ms365_polling_started", interval=settings.ms365_sync_interval_seconds)

    yield  # App runs here

    # Cancel background tasks on shutdown
    if ms365_sync_task:
        ms365_sync_task.cancel()
    logger.info("api_shutdown")

# Create FastAPI app
app = FastAPI(
    title="Croo Digital Experience API",
    description="Agent-First CRM/ERP — AI-powered digital experience platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — strict methods & headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Import and include routers
from app.presentation.routes.auth_routes import router as auth_router
from app.presentation.routes.search_routes import router as search_router
from app.presentation.routes.enrichment_routes import router as enrichment_router
from app.presentation.routes.organization_routes import router as organization_router
from app.presentation.routes.contact_routes import router as contact_router
from app.presentation.routes.opportunity_routes import router as opportunity_router
from app.presentation.routes.quote_routes import router as quote_router
from app.presentation.routes.activity_routes import router as activity_router
from app.presentation.routes.user_routes import router as user_router
from app.presentation.routes.contact_ai_routes import router as contact_ai_router
from app.presentation.routes.department_routes import router as department_router
from app.presentation.routes.capability_routes import router as capability_router
from app.presentation.routes.workflow_routes import router as workflow_router
from app.presentation.routes.webhook_routes import router as webhook_router
from app.presentation.routes.kb_routes import router as kb_router
from app.presentation.routes.bob_routes import router as bob_router
from app.presentation.routes.bob_settings_routes import router as bob_settings_router
from app.presentation.routes.voice_routes import router as voice_router
from app.presentation.routes.bcc_routes import router as bcc_router
from app.presentation.routes.training_routes import router as training_router
from app.presentation.routes.role_routes import router as role_router
from app.presentation.routes.tenant_routes import router as tenant_router
from app.presentation.routes.product_routes import router as product_router
from app.presentation.routes.usage_routes import router as usage_router
from app.presentation.routes.ms365_routes import router as ms365_router
from app.presentation.routes.smart_label_routes import router as smart_label_router
from app.middleware.metrics import router as metrics_router
from app.presentation.routes.client_map_routes import router as client_map_router

app.include_router(auth_router, tags=["auth"])
app.include_router(search_router, tags=["search"])
app.include_router(enrichment_router, tags=["enrichment"])
app.include_router(organization_router, tags=["organizations"])
app.include_router(contact_router, tags=["contacts"])
app.include_router(contact_ai_router, tags=["contacts-ai"])
app.include_router(opportunity_router, tags=["opportunities"])
app.include_router(quote_router, tags=["quotes"])
app.include_router(activity_router, tags=["activities"])
app.include_router(user_router, tags=["users"])
app.include_router(department_router, tags=["departments"])
app.include_router(capability_router, tags=["capabilities"])
app.include_router(workflow_router, tags=["workflows"])
app.include_router(webhook_router, tags=["webhooks"])
app.include_router(kb_router, tags=["knowledge-base"])
app.include_router(bob_router, tags=["bob"])
app.include_router(bob_settings_router, tags=["bob-settings"])
app.include_router(voice_router, tags=["voice"])
app.include_router(bcc_router, tags=["bcc"])
app.include_router(training_router, tags=["training"])
app.include_router(role_router, tags=["roles"])
app.include_router(tenant_router, tags=["tenants"])
app.include_router(product_router, tags=["products"])
app.include_router(usage_router, tags=["usage"])
app.include_router(ms365_router, tags=["ms365"])
app.include_router(smart_label_router, tags=["inbox-labels"])
app.include_router(metrics_router, tags=["metrics"])
app.include_router(client_map_router, tags=["client-map"])


@app.get("/health", tags=["monitoring"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "croo-digital-experience-api"}


