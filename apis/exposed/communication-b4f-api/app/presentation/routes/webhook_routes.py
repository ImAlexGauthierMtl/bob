"""Webhook routes — external workflow triggers via API.

Allows external systems to trigger workflows via HTTP POST.
Supports API key auth. Workflow execution is owned by workflow-backend-api.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, Field

from app.middleware.auth import get_current_user
from shared.config import get_settings
settings = get_settings("communication")

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ── Schemas ──────────────────────────

class WebhookPayload(BaseModel):
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
    status: str
    event: str
    executions_triggered: int
    execution_ids: list[str]
    received_at: str


# ── Routes ───────────────────────────

@router.post("/trigger", response_model=WebhookResponse)
async def trigger_webhook(
    payload: WebhookPayload,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Trigger workflows via authenticated webhook."""
    logger.info(
        "webhook_received",
        event_name=payload.event,
        source=payload.source,
        user=current_user["email"],
    )

    try:
        return WebhookResponse(
            status="accepted",
            event=payload.event,
            executions_triggered=0,
            execution_ids=[],
            received_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.error("webhook_error", event_name=payload.event, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}",
        )


@router.post("/trigger/public", response_model=WebhookResponse)
async def trigger_webhook_public(
    payload: WebhookPayload,
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """Trigger workflows via API key (no JWT required)."""
    expected_key = getattr(settings, "webhook_api_key", None)
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    logger.info(
        "webhook_public_received",
        event_name=payload.event,
        source=payload.source,
    )

    try:
        return WebhookResponse(
            status="accepted",
            event=payload.event,
            executions_triggered=0,
            execution_ids=[],
            received_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.error("webhook_public_error", event_name=payload.event, error=str(e))
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
