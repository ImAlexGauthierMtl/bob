"""Main FastAPI application for Croo Digital Experience API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

import structlog

logger = structlog.get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Croo Digital Experience API",
    description="Agent-First CRM/ERP — AI-powered digital experience platform",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/health", tags=["monitoring"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "croo-digital-experience-api"}


@app.on_event("startup")
async def startup_event():
    """Startup event — create tables and seed admin user."""
    from app.infrastructure.database import engine, SessionLocal
    from app.domain.entities.base import Base
    # Import entities so they register with Base.metadata
    from app.domain.entities import user, organization, contact, opportunity, quote, activity, department, capability, bob_settings  # noqa: F401
    from app.domain.entities import workflow, workflow_execution  # noqa: F401
    from app.domain.entities import bcc_entities  # noqa: F401
    from app.domain.entities import training_models  # noqa: F401
    from app.infrastructure.seed import run_seed
    from app.infrastructure.seed_capabilities import seed_capabilities
    from app.infrastructure.seed_workflows import seed_workflows
    from app.infrastructure.seed_bcc import seed_bcc

    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("database_tables_created")

    # Seed admin + capabilities + workflows
    db = SessionLocal()
    try:
        run_seed(db)
        seed_capabilities(db)
        # Seed workflows — use admin user's tenant for default tenant
        admin = db.query(user.User).filter(user.User.email == settings.admin_email).first()
        if admin:
            seed_workflows(db, tenant_id=admin.tenant_id)
            seed_bcc(db, tenant_id=admin.tenant_id)
    finally:
        db.close()
    logger.info("api_started", environment=settings.environment)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event."""
    logger.info("api_shutdown")

