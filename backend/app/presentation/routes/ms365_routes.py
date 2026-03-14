"""MS365 routes — OAuth flow, sync, email/event CRUD."""

from typing import Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import structlog

from app.config import settings
from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.infrastructure.persistence.ms365_repository import MS365Repository
from app.infrastructure.external.ms365_graph_service import MS365GraphService
from app.application.services.ms365_sync_service import MS365SyncService
from app.presentation.schemas.ms365_schemas import (
    MS365AuthUrlResponse,
    MS365ConnectionResponse,
    SyncedEmailResponse,
    SyncedEmailListResponse,
    SyncedEventResponse,
    SyncedEventListResponse,
    SyncStatusResponse,
    EmailAiInsightResponse,
    SendEmailRequest,
    ReplyEmailRequest,
    ForwardEmailRequest,
)

from app.agents.llm_client import llm_client
import json

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/ms365")
graph_service = MS365GraphService()


# ── OAuth2 Flow ──────────────────────────────────────────────────

@router.get("/auth-url", response_model=MS365AuthUrlResponse)
async def get_auth_url(
    current_user: dict = Depends(get_current_user),
):
    """Generate Microsoft OAuth2 authorization URL.

    The frontend redirects the user to this URL for consent.
    State contains user_id for callback matching.
    """
    auth_url = graph_service.build_auth_url(state=current_user["user_id"])
    return MS365AuthUrlResponse(auth_url=auth_url)


@router.get("/callback")
async def oauth_callback(
    code: str = Query(...),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """OAuth2 callback — exchanges code for tokens and creates connection.

    This endpoint is called by Microsoft after user consent.
    Redirects back to the frontend integrations page.
    """
    try:
        logger.info("ms365_callback_received", state=state, has_code=bool(code))
        # Exchange code for tokens
        token_data = await graph_service.exchange_code_for_tokens(code)

        # Get user profile from MS Graph
        profile = await graph_service.get_user_profile(token_data["access_token"])
        logger.info("ms365_profile_fetched", profile_id=profile.get("id"), email=profile.get("mail"))

        # state contains user_id from auth_url
        user_id = state
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing state parameter")

        repo = MS365Repository(db)

        # Check for existing connection (re-connect case)
        from app.domain.entities.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        existing_conn = repo.get_connection_by_user(user_id, user.tenant_id)

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600))

        if existing_conn:
            repo.update_connection(existing_conn, {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "token_expires_at": expires_at,
                "scopes": token_data.get("scope", ""),
                "ms_user_id": profile.get("id"),
                "ms_email": profile.get("mail") or profile.get("userPrincipalName"),
                "is_active": True,
                "is_deleted": False,
                "deleted_at": None,
                "deleted_by": None,
            })
        else:
            repo.create_connection({
                "user_id": user_id,
                "ms_user_id": profile.get("id"),
                "ms_email": profile.get("mail") or profile.get("userPrincipalName"),
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "token_expires_at": expires_at,
                "scopes": token_data.get("scope", ""),
                "is_active": True,
            }, tenant_id=user.tenant_id)

        logger.info("ms365_connected", user_id=user_id, ms_email=profile.get("mail"))

        # Redirect to frontend integrations page
        frontend_url = getattr(settings, "frontend_url", "http://localhost:4700")
        return RedirectResponse(url=f"{frontend_url}/settings/integrations?ms365=connected")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("ms365_callback_error", error=str(e))
        frontend_url = getattr(settings, "frontend_url", "http://localhost:4700")
        return RedirectResponse(url=f"{frontend_url}/settings/integrations?ms365=error")


# ── Connection Management ────────────────────────────────────────

@router.get("/connection", response_model=Optional[MS365ConnectionResponse])
async def get_connection(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's MS365 connection status."""
    repo = MS365Repository(db)
    conn = repo.get_connection_by_user(current_user["user_id"], current_user["tenant_id"])
    if not conn:
        return None
    return MS365ConnectionResponse.model_validate(conn)


@router.delete("/connection", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect MS365 — soft-deletes the connection, preserves data."""
    repo = MS365Repository(db)
    conn = repo.get_connection_by_user(current_user["user_id"], current_user["tenant_id"])
    if not conn:
        raise HTTPException(status_code=404, detail="No MS365 connection found")
    repo.soft_delete_connection(conn, current_user["email"])
    logger.info("ms365_disconnected", user_id=current_user["user_id"])


# ── Sync ─────────────────────────────────────────────────────────

@router.post("/sync", response_model=SyncStatusResponse)
async def force_sync(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Force an immediate sync of emails and calendar for the current user."""
    repo = MS365Repository(db)
    conn = repo.get_connection_by_user(current_user["user_id"], current_user["tenant_id"])
    if not conn or not conn.is_active:
        raise HTTPException(status_code=404, detail="No active MS365 connection")

    sync_service = MS365SyncService(db)
    try:
        emails_count = await sync_service.sync_emails(conn)
        events_count = await sync_service.sync_calendar(conn)
        return SyncStatusResponse(
            emails_synced=emails_count,
            events_synced=events_count,
            status="completed",
        )
    except Exception as e:
        logger.error("ms365_force_sync_error", user_id=current_user["user_id"], error=str(e))
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


# ── Emails ───────────────────────────────────────────────────────

@router.get("/emails", response_model=SyncedEmailListResponse)
async def list_emails(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    folder: Optional[str] = None,
    search: Optional[str] = None,
    smart_label: Optional[str] = None,
    linked_contact_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List synced emails for the current user."""
    repo = MS365Repository(db)
    items = repo.list_emails(current_user["user_id"], current_user["tenant_id"], skip, limit, folder, search, linked_contact_id, smart_label)
    total = repo.count_emails(current_user["user_id"], current_user["tenant_id"], folder, search, linked_contact_id, smart_label)
    return SyncedEmailListResponse(
        items=[SyncedEmailResponse.model_validate(e) for e in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/emails/{email_id}", response_model=SyncedEmailResponse)
async def get_email(
    email_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific synced email."""
    repo = MS365Repository(db)
    email = repo.get_email_by_id(email_id, current_user["user_id"], current_user["tenant_id"])
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return SyncedEmailResponse.model_validate(email)


@router.post("/emails/{email_id}/ai-insights", response_model=EmailAiInsightResponse)
async def generate_email_ai_insights(
    email_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an AI summary, smart label, and action items for an email using Groq."""
    repo = MS365Repository(db)
    email = repo.get_email_by_id(email_id, current_user["user_id"], current_user["tenant_id"])
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    content = email.body_html or email.body_preview or email.subject

    if not content or not str(content).strip():
        return EmailAiInsightResponse(
            summary="This email has no readable content.",
            smart_label="Empty",
            action_items=[]
        )

    system_prompt = """You are an intelligent email assistant.
Your job is to read the provided email content and extract three things:
1. `summary`: A concise 1-2 sentence summary of what the email is about.
2. `smart_label`: A single category tag such as "Urgent", "Client", "Opportunity", "Internal", "Spam", or "General".
3. `action_items`: An array of string action items that need to be done. If none, return an empty array.

Respond ONLY with valid JSON.
"""

    user_prompt = f"Subject: {email.subject}\nSender: {email.from_name} ({email.from_address})\nContent:\n{content}"

    try:
        response = llm_client.chat(
            prompt=user_prompt,
            system_prompt=system_prompt,
            json_mode=True,
            temperature=0.0,
            max_tokens=500,
        )
        extracted = json.loads(response)
        return EmailAiInsightResponse(
            summary=extracted.get("summary", "Summary could not be generated."),
            smart_label=extracted.get("smart_label", "General"),
            action_items=extracted.get("action_items", [])
        )
    except Exception as e:
        logger.error("ms365_email_ai_error", email_id=email_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate AI insights.")


@router.post("/emails/send")
async def send_email(
    request: SendEmailRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compose and send a new email."""
    repo = MS365Repository(db)
    conn = repo.get_connection_by_user(current_user["user_id"], current_user["tenant_id"])
    if not conn or not conn.is_active:
        raise HTTPException(status_code=400, detail="No active MS365 connection.")

    try:
        access_token, new_data = await graph_service.ensure_valid_token(
            conn.access_token, conn.refresh_token, conn.expires_at
        )
        if new_data:
            repo.update_connection_tokens(conn, new_data)
        
        return await graph_service.send_mail(
            access_token=access_token,
            subject=request.subject,
            body_content=request.body_content,
            to_recipients=request.to_recipients,
            cc_recipients=request.cc_recipients,
            bcc_recipients=request.bcc_recipients,
            body_type=request.body_type
        )
    except Exception as e:
        logger.error("ms365_send_email_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emails/{email_id}/reply")
async def reply_email(
    email_id: str,
    request: ReplyEmailRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reply to an existing email."""
    repo = MS365Repository(db)
    conn = repo.get_connection_by_user(current_user["user_id"], current_user["tenant_id"])
    if not conn or not conn.is_active:
        raise HTTPException(status_code=400, detail="No active MS365 connection.")
    
    email = repo.get_email_by_id(email_id, current_user["user_id"], current_user["tenant_id"])
    if not email:
        raise HTTPException(status_code=404, detail="Email not found.")

    try:
        access_token, new_data = await graph_service.ensure_valid_token(
            conn.access_token, conn.refresh_token, conn.expires_at
        )
        if new_data:
            repo.update_connection_tokens(conn, new_data)

        return await graph_service.reply_mail(
            access_token=access_token,
            message_id=email.ms_message_id,
            comment=request.comment,
            reply_all=request.reply_all
        )
    except Exception as e:
        logger.error("ms365_reply_email_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emails/{email_id}/forward")
async def forward_email(
    email_id: str,
    request: ForwardEmailRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Forward an existing email."""
    repo = MS365Repository(db)
    conn = repo.get_connection_by_user(current_user["user_id"], current_user["tenant_id"])
    if not conn or not conn.is_active:
        raise HTTPException(status_code=400, detail="No active MS365 connection.")
    
    email = repo.get_email_by_id(email_id, current_user["user_id"], current_user["tenant_id"])
    if not email:
        raise HTTPException(status_code=404, detail="Email not found.")

    try:
        access_token, new_data = await graph_service.ensure_valid_token(
            conn.access_token, conn.refresh_token, conn.expires_at
        )
        if new_data:
            repo.update_connection_tokens(conn, new_data)

        return await graph_service.forward_mail(
            access_token=access_token,
            message_id=email.ms_message_id,
            to_recipients=request.to_recipients,
            comment=request.comment
        )
    except Exception as e:
        logger.error("ms365_forward_email_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ── Calendar Events ──────────────────────────────────────────────

@router.get("/events", response_model=SyncedEventListResponse)
async def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List synced calendar events for the current user."""
    repo = MS365Repository(db)
    items = repo.list_events(current_user["user_id"], current_user["tenant_id"], skip, limit, from_date, to_date)
    total = repo.count_events(current_user["user_id"], current_user["tenant_id"], from_date, to_date)
    return SyncedEventListResponse(
        items=[SyncedEventResponse.model_validate(e) for e in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/events/{event_id}", response_model=SyncedEventResponse)
async def get_event(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific synced calendar event."""
    repo = MS365Repository(db)
    event = repo.get_event_by_id(event_id, current_user["user_id"], current_user["tenant_id"])
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return SyncedEventResponse.model_validate(event)


# ── Webhook Endpoint ─────────────────────────────────────────────

@router.post("/webhook")
async def ms365_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Receive MS Graph change notifications.

    Handles both:
    1. Validation request (GET with validationToken)
    2. Notification push (POST with notification payload)
    """
    # Handle validation request from MS Graph
    params = request.query_params
    validation_token = params.get("validationToken")
    if validation_token:
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=validation_token, status_code=200)

    # Handle notification payload
    body = await request.json()
    notifications = body.get("value", [])

    if not notifications:
        return {"status": "ok"}

    # Validate client state
    for n in notifications:
        if n.get("clientState") != settings.webhook_api_key:
            logger.warning("ms365_webhook_invalid_client_state")
            raise HTTPException(status_code=403, detail="Invalid client state")

    # Process async
    import asyncio
    sync_service = MS365SyncService(db)
    asyncio.ensure_future(sync_service.handle_webhook_notification(notifications))

    return {"status": "ok"}
