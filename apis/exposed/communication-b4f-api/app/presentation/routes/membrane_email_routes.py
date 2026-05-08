"""Membrane email proxy routes — send, reply, forward via Membrane actions.

These routes mirror the MS365 email routes but proxy through Membrane instead
of MS Graph API. This allows the frontend to use a single provider-agnostic
interface while Membrane handles the provider-specific implementation.
"""

from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
import httpx
import structlog

from shared.config import get_settings
from app.middleware.auth import get_current_user
from app.infrastructure.external.membrane_service import (
    generate_membrane_token,
    MembraneClient,
)
from app.presentation.schemas.ms365_schemas import (
    SendEmailRequest,
    ReplyEmailRequest,
    ForwardEmailRequest,
    SyncedEmailListResponse,
    SyncedEventListResponse,
)
from app.infrastructure.clients.email_client import email_crud_client, event_crud_client

logger = structlog.get_logger(__name__)
settings = get_settings("communication")

# Separate router for email actions — included under /api/v1/membrane by membrane_routes.py
email_router = APIRouter(prefix="/emails")

# Default integration key for email/calendar
EMAIL_INTEGRATION_KEY = "microsoft-outlook"


def _resolve_email_tenant_key(user: dict) -> str:
    """Email is per-user by default."""
    return user["user_id"]


async def _get_email_connection(user: dict) -> Optional[dict]:
    """Find the active email connection for this user via Membrane."""
    tenant_key = _resolve_email_tenant_key(user)
    token = generate_membrane_token(
        tenant_key=tenant_key,
        name=user.get("email", tenant_key),
        fields={"croo_user_id": user["user_id"]},
        expires_minutes=5,
    )
    client = MembraneClient(token)
    try:
        connections = await client.list_connections()
        for conn in connections:
            if not conn.get("disconnected"):
                return conn
        return None
    finally:
        await client.close()


# ── Read operations (from DB, unchanged) ─────────────────────────

@email_router.get("", response_model=SyncedEmailListResponse)
async def list_emails(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    folder: Optional[str] = None,
    search: Optional[str] = None,
    smart_label: Optional[str] = None,
    linked_contact_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """List synced emails from Croo DB (Membrane webhooks populate this)."""
    data = await email_crud_client.list(
        current_user["user_id"], skip, limit, folder, search, smart_label, linked_contact_id,
        forward_headers=request.headers,
    )
    return data


@email_router.get("/events", response_model=SyncedEventListResponse)
async def list_events(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user),
):
    """List synced calendar events from Croo DB."""
    data = await event_crud_client.list(
        current_user["user_id"], skip, limit, from_date, to_date,
        forward_headers=request.headers,
    )
    return data


# ── Write operations (via Membrane actions) ──────────────────────

@email_router.post("/send")
async def send_email(
    send_request: SendEmailRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Send an email via Membrane universal action.

    Membrane resolves the correct provider (Outlook, Gmail, etc.)
    based on the tenant's active connection.
    """
    tenant_key = _resolve_email_tenant_key(current_user)
    token = generate_membrane_token(
        tenant_key=tenant_key,
        name=current_user.get("email", tenant_key),
        fields={"croo_user_id": current_user["user_id"]},
        expires_minutes=10,
    )
    client = MembraneClient(token)
    try:
        # Find the email connection
        connections = await client.list_connections()
        email_conn = None
        for conn in connections:
            if not conn.get("disconnected"):
                email_conn = conn
                break
        if not email_conn:
            raise HTTPException(status_code=400, detail="No active email connection. Please connect your email account in Settings > Integrations.")

        # Map Croo schema to Membrane universal action input
        membrane_input = {
            "subject": send_request.subject,
            "body": send_request.body_content,
            "to": [{"email": addr} for addr in send_request.to_recipients],
        }
        if send_request.cc_recipients:
            membrane_input["cc"] = [{"email": addr} for addr in send_request.cc_recipients]
        if send_request.bcc_recipients:
            membrane_input["bcc"] = [{"email": addr} for addr in send_request.bcc_recipients]

        result = await client.run_action(
            action_key="send-email",
            input_data=membrane_input,
            connection_id=email_conn["id"],
        )
        logger.info("membrane_email_sent", tenant_key=tenant_key, connection_id=email_conn["id"])
        return {"status": "sent", "membrane_output": result}
    except httpx.HTTPStatusError as exc:
        detail = "Failed to send email"
        try:
            detail = exc.response.json().get("message", detail)
        except Exception:
            detail = exc.response.text[:200]
        logger.error("membrane_send_email_error", status=exc.response.status_code, detail=detail)
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    finally:
        await client.close()


@email_router.post("/{email_id}/reply")
async def reply_email(
    email_id: str,
    reply_request: ReplyEmailRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Reply to an email via Membrane action."""
    email = await email_crud_client.get(email_id, current_user["user_id"], forward_headers=request.headers)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found.")

    tenant_key = _resolve_email_tenant_key(current_user)
    token = generate_membrane_token(
        tenant_key=tenant_key,
        name=current_user.get("email", tenant_key),
        fields={"croo_user_id": current_user["user_id"]},
        expires_minutes=10,
    )
    client = MembraneClient(token)
    try:
        connections = await client.list_connections()
        email_conn = None
        for conn in connections:
            if not conn.get("disconnected"):
                email_conn = conn
                break
        if not email_conn:
            raise HTTPException(status_code=400, detail="No active email connection.")

        membrane_input = {
            "messageId": email.get("ms_message_id"),
            "comment": reply_request.comment,
            "replyAll": reply_request.reply_all,
        }

        result = await client.run_action(
            action_key="reply-email",
            input_data=membrane_input,
            connection_id=email_conn["id"],
        )
        logger.info("membrane_email_replied", tenant_key=tenant_key, email_id=email_id)
        return {"status": "replied", "membrane_output": result}
    except httpx.HTTPStatusError as exc:
        detail = "Failed to reply to email"
        try:
            detail = exc.response.json().get("message", detail)
        except Exception:
            detail = exc.response.text[:200]
        logger.error("membrane_reply_email_error", status=exc.response.status_code, detail=detail)
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    finally:
        await client.close()


@email_router.post("/{email_id}/forward")
async def forward_email(
    email_id: str,
    fwd_request: ForwardEmailRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Forward an email via Membrane action."""
    email = await email_crud_client.get(email_id, current_user["user_id"], forward_headers=request.headers)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found.")

    tenant_key = _resolve_email_tenant_key(current_user)
    token = generate_membrane_token(
        tenant_key=tenant_key,
        name=current_user.get("email", tenant_key),
        fields={"croo_user_id": current_user["user_id"]},
        expires_minutes=10,
    )
    client = MembraneClient(token)
    try:
        connections = await client.list_connections()
        email_conn = None
        for conn in connections:
            if not conn.get("disconnected"):
                email_conn = conn
                break
        if not email_conn:
            raise HTTPException(status_code=400, detail="No active email connection.")

        membrane_input = {
            "messageId": email.get("ms_message_id"),
            "to": [{"email": addr} for addr in fwd_request.to_recipients],
            "comment": fwd_request.comment,
        }

        result = await client.run_action(
            action_key="forward-email",
            input_data=membrane_input,
            connection_id=email_conn["id"],
        )
        logger.info("membrane_email_forwarded", tenant_key=tenant_key, email_id=email_id)
        return {"status": "forwarded", "membrane_output": result}
    except httpx.HTTPStatusError as exc:
        detail = "Failed to forward email"
        try:
            detail = exc.response.json().get("message", detail)
        except Exception:
            detail = exc.response.text[:200]
        logger.error("membrane_forward_email_error", status=exc.response.status_code, detail=detail)
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    finally:
        await client.close()
