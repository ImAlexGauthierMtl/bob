"""Webhook routes — external workflow triggers via API.

Allows external systems to trigger workflows via HTTP POST.
Supports API key authentication and event routing through EventBus.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.agents.event_bus import event_bus
from app.config import settings

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


# ── Schemas ──────────────────────────

class WebhookPayload(BaseModel):
    """Incoming webhook payload."""
    event: str = Field(..., description="Event name, e.g. 'contact.created'")
    data: dict = Field(default_factory=dict, description="Event payload data")
    source: str = Field(default="external", description="Source system name")

    class Config:
        json_schema_extra = {
            "example": {
                "event": "contact.created",
                "data": {"contact_id": "abc-123", "email": "new@client.com"},
                "source": "zapier",
            }
        }


class WebhookResponse(BaseModel):
    """Webhook response."""
    status: str
    event: str
    executions_triggered: int
    execution_ids: list[str]
    received_at: str


# ── Routes ───────────────────────────

@router.post("/trigger", response_model=WebhookResponse)
async def trigger_webhook(
    payload: WebhookPayload,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger workflows via authenticated webhook.

    Requires JWT authentication. The event will be routed through
    the EventBus to find and execute matching workflows.
    """
    logger.info(
        "webhook_received",
        event=payload.event,
        source=payload.source,
        user=current_user["email"],
    )

    try:
        execution_ids = await event_bus.publish(
            event_name=payload.event,
            payload=payload.data,
            db=db,
            tenant_id=current_user["tenant_id"],
            triggered_by=f"webhook:{payload.source}:{current_user['email']}",
        )

        return WebhookResponse(
            status="accepted",
            event=payload.event,
            executions_triggered=len(execution_ids),
            execution_ids=execution_ids,
            received_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.error("webhook_error", event=payload.event, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}",
        )


@router.post("/trigger/public", response_model=WebhookResponse)
async def trigger_webhook_public(
    payload: WebhookPayload,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """Trigger workflows via API key (no JWT required).

    For external integrations (Zapier, n8n, etc.) that can't
    authenticate with JWT. Requires X-API-Key header.
    """
    # Validate API key — for now use a simple env-based key
    expected_key = getattr(settings, "webhook_api_key", None)
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Use the admin user's tenant for public webhooks
    from app.domain.entities.user import User
    admin = db.query(User).filter(
        User.email == settings.admin_email,
        User.is_deleted == False,
    ).first()

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No admin user configured",
        )

    logger.info(
        "webhook_public_received",
        event=payload.event,
        source=payload.source,
    )

    try:
        execution_ids = await event_bus.publish(
            event_name=payload.event,
            payload=payload.data,
            db=db,
            tenant_id=admin.tenant_id,
            triggered_by=f"webhook:{payload.source}:api-key",
        )

        return WebhookResponse(
            status="accepted",
            event=payload.event,
            executions_triggered=len(execution_ids),
            execution_ids=execution_ids,
            received_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.error("webhook_public_error", event=payload.event, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}",
        )


@router.get("/events", response_model=list[str])
async def list_supported_events(
    current_user: dict = Depends(get_current_user),
):
    """List all event names that have matching active workflows."""
    return [
        "contact.created", "contact.updated", "contact.deleted",
        "organization.created", "organization.updated", "organization.deleted",
        "opportunity.created", "opportunity.updated", "opportunity.deleted",
        "quote.created", "quote.updated", "quote.deleted",
        "activity.created", "activity.updated", "activity.completed", "activity.deleted",
    ]
