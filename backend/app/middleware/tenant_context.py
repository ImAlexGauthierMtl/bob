"""Tenant context middleware — sets tenant_id on every DB session for RLS.

This middleware extracts the tenant_id from the authenticated user
and sets it as a PostgreSQL session variable (`app.current_tenant_id`).
RLS policies use this variable to filter rows automatically.
"""

from fastapi import Request, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db

import structlog

logger = structlog.get_logger(__name__)


async def get_db_with_tenant(request: Request) -> Session:
    """Enhanced get_db that sets tenant context for RLS.

    This should be used in place of get_db in routes that need
    tenant isolation. It reads tenant_id from the request state
    (set by auth middleware) and configures the DB session.
    """
    from app.infrastructure.database import SessionLocal

    db = SessionLocal()
    try:
        # Extract tenant_id from the authenticated user
        # The auth dependency sets this on the request
        tenant_id = getattr(request.state, "tenant_id", None)

        if tenant_id:
            db.execute(text("SET app.current_tenant_id = :tid"), {"tid": tenant_id})
            db.execute(text("SET app.current_user_id = :uid"), {"uid": getattr(request.state, "user_id", "")})

        yield db
    finally:
        # Reset session variables to prevent leakage
        try:
            db.execute(text("RESET app.current_tenant_id"))
            db.execute(text("RESET app.current_user_id"))
        except Exception:
            pass
        db.close()
