import os
"""Auth B4F API — auth, authorization, JWT management.

B4F layer — business logic only, delegates CRUD to user~backend-api.
Port: 8001
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router

settings = get_settings("auth")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


async def seed_admin_user():
    """Create or update the admin user on startup."""
    from app.config import settings as auth_settings
    from app.infrastructure.clients.user_client import user_client
    from datetime import datetime, timedelta, timezone
    from jose import jwt

    email = auth_settings.admin_email
    password = auth_settings.admin_password

    if not email or not password:
        logger.info("admin_seed.skipped", reason="ADMIN_EMAIL or ADMIN_PASSWORD not set")
        return

    # Retry — user-backend-api may not be ready yet
    for attempt in range(5):
        try:
            existing = await user_client.get_by_email(email)
            if existing:
                # Generate a system JWT signed with jwt_secret_key (shared)
                # so user-backend-api accepts it for the PATCH call
                token_data = {
                    "sub": existing["id"],
                    "email": existing["email"],
                    "tenant_id": existing.get("tenant_id", "default"),
                    "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
                    "type": "access",
                }
                system_token = jwt.encode(
                    token_data,
                    settings.jwt_secret_key,
                    algorithm=settings.jwt_algorithm,
                )
                auth_headers = {"authorization": f"Bearer {system_token}"}

                logger.info("admin_seed.updating", email=email, user_id=existing["id"])
                update_data = {
                    "password": password,
                    "first_name": auth_settings.admin_first_name,
                    "last_name": auth_settings.admin_last_name,
                    "is_super_admin": True,
                }
                if not existing.get("active_organization_id"):
                    update_data["active_organization_id"] = "00000000-0000-0000-0000-000000000001"
                await user_client.update(existing["id"], update_data, forward_headers=auth_headers)
                logger.info("admin_seed.updated", email=email)
            else:
                logger.info("admin_seed.creating", email=email)
                created = await user_client.create({
                    "email": email,
                    "password": password,
                    "first_name": auth_settings.admin_first_name,
                    "last_name": auth_settings.admin_last_name,
                    "is_super_admin": True,
                    "role": "admin",
                    "created_by": "system",
                    "active_organization_id": "00000000-0000-0000-0000-000000000001",
                })
                logger.info("admin_seed.created", email=email, user_id=created["id"])
            return
        except Exception as e:
            logger.warning("admin_seed.retry", attempt=attempt + 1, error=str(e))
            await asyncio.sleep(3 * (attempt + 1))

    logger.error("admin_seed.failed", reason="All retries exhausted")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed_admin_user()
    yield


app = FastAPI( 
    title="Auth B4F API",
    description="Authentication & Authorization — Croo Digital Experience",
    version="1.0.0",
    lifespan=lifespan,
)

setup_cors(app, "auth")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])
_api_prefix = os.environ.get("API_ROUTE_PREFIX", "")
if _api_prefix:
    app.include_router(monitoring_router, prefix=f"/api/v1/{_api_prefix}", tags=["monitoring"])

from app.presentation.routes.auth_routes import router as auth_router
from app.presentation.routes.bob_cloud_auth_routes import router as bob_cloud_auth_router
from app.presentation.routes.user_routes import router as user_router
from app.presentation.routes.tenant_routes import router as tenant_router
from app.presentation.routes.role_routes import router as role_router
app.include_router(auth_router, tags=["auth"])
app.include_router(bob_cloud_auth_router, tags=["auth"])
app.include_router(user_router, tags=["users"])
app.include_router(tenant_router, tags=["tenants"])
app.include_router(role_router, tags=["roles"])
