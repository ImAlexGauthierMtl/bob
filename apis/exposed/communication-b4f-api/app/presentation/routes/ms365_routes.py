"""MS365 routes — OAuth flow, sync orchestration, email/event proxying via HTTP client."""

import os
import asyncio
from typing import Optional, Union
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse
import structlog

from shared.config import get_settings
settings = get_settings("communication")
from app.middleware.auth import get_current_user
from app.infrastructure.clients.email_client import connection_client, email_crud_client, event_crud_client
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

# ── Helpers ───────────────────────────────────────────────────────

def _parse_token_expiry(value: Union[str, datetime, None]) -> datetime:
    """Parse token_expires_at from various formats into a timezone-aware datetime."""
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value)
    except Exception:
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid token_expires_at format")


# ── OAuth2 Flow ──────────────────────────────────────────────────

@router.get("/auth-url", response_model=MS365AuthUrlResponse)
async def get_auth_url(
    current_user: dict = Depends(get_current_user),
):
    has_cid = bool(graph_service._client_id)
    has_sec = bool(graph_service._client_secret)
    has_uri = bool(graph_service._redirect_uri)
    logger.info(
        "ms365_auth_url_env_check",
        has_client_id=has_cid,
        has_client_secret=has_sec,
        has_redirect_uri=has_uri,
    )
    if not has_cid or not has_sec or not has_uri:
        raise HTTPException(status_code=503, detail="MS365 configuration missing. Please set CLIENT_ID, CLIENT_SECRET, and REDIRECT_URI.")
    auth_url = graph_service.build_auth_url(state=current_user["user_id"])
    return MS365AuthUrlResponse(auth_url=auth_url)


@router.get("/callback")
async def oauth_callback(
    request: Request,
    code: str = Query(...),
    state: Optional[str] = Query(None),
):
    """OAuth2 callback — exchanges code for tokens and creates/updates connection via backend.
    Uses service-to-service authentication (system JWT) when calling the email-backend-api.
    """
    from jose import jwt
    try:
        logger.info("ms365_callback_received", state=state, has_code=bool(code))
        # #region agent log cf6b4c – step 1: token exchange
        logger.info("ms365_cb_step", step="1_exchange_start")
        # #endregion
        token_data = await graph_service.exchange_code_for_tokens(code)
        # #region agent log cf6b4c – step 2: profile fetch
        logger.info("ms365_cb_step", step="2_exchange_ok", has_access_token=bool(token_data.get("access_token")))
        # #endregion
        profile = await graph_service.get_user_profile(token_data["access_token"])
        logger.info("ms365_profile_fetched", profile_id=profile.get("id"), email=profile.get("mail"))

        user_id = state
        if not user_id:
            raise HTTPException(status_code=400, detail="Missing state parameter")

        # #region agent log cf6b4c – step 3: JWT generation
        logger.info("ms365_cb_step", step="3_jwt_gen", user_id=user_id, has_secret=bool(settings.jwt_secret_key))
        # #endregion
        token_payload = {
            "sub": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "type": "access",
        }
        system_jwt = jwt.encode(token_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        service_headers = {"Authorization": f"Bearer {system_jwt}"}

        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600))).isoformat()

        # #region agent log cf6b4c – step 4: get existing connection
        logger.info("ms365_cb_step", step="4_get_conn", user_id=user_id)
        # #endregion
        existing_conn = await connection_client.get_by_user(user_id, forward_headers=service_headers)
        # #region agent log cf6b4c – step 5: connection result
        logger.info("ms365_cb_step", step="5_conn_result", has_existing=bool(existing_conn))
        # #endregion

        conn_data = {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "token_expires_at": expires_at,
            "scopes": token_data.get("scope", ""),
            "ms_user_id": profile.get("id"),
            "ms_email": profile.get("mail") or profile.get("userPrincipalName"),
            "is_active": True,
        }

        if existing_conn:
            await connection_client.update(existing_conn["id"], conn_data, forward_headers=service_headers)
        else:
            conn_data["user_id"] = user_id
            await connection_client.create(conn_data, forward_headers=service_headers)

        # #region agent log cf6b4c – step 6: success
        logger.info("ms365_cb_step", step="6_saved_ok")
        # #endregion
        logger.info("ms365_connected", user_id=user_id, ms_email=profile.get("mail"))

        # Fetch the full connection detail (with id, user_id, tokens) for sync
        full_conn = await connection_client.get_by_user(user_id, forward_headers=service_headers)
        if full_conn:
            # Merge token fields that may not be in the response
            full_conn.setdefault("access_token", conn_data["access_token"])
            full_conn.setdefault("refresh_token", conn_data.get("refresh_token"))
            full_conn.setdefault("token_expires_at", conn_data["token_expires_at"])
            sync_service = MS365SyncService(service_headers)
            asyncio.create_task(sync_service.sync_emails(full_conn))
            asyncio.create_task(sync_service.sync_calendar(full_conn))

        frontend_url = os.environ.get("INGRESS_URL", "http://localhost:4700").rstrip("/")
        # #region agent log cf6b4c – step 7: redirect
        logger.info("ms365_cb_step", step="7_redirect", frontend_url=frontend_url)
        # #endregion
        return RedirectResponse(url=f"{frontend_url}/settings/integrations?ms365=connected")

    except HTTPException:
        raise
    except Exception as e:
        # #region agent log cf6b4c – callback error detail
        import traceback
        tb_str = traceback.format_exc()
        logger.error("ms365_callback_error", error=str(e), error_type=type(e).__name__, tb=tb_str)
        # #endregion
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=502, content={
            "debug": True,
            "error_type": type(e).__name__,
            "error": str(e)[:1000],
            "traceback": tb_str[-2000:],
            "code_length": len(code),
            "code_first20": code[:20],
            "state": state,
        })


# ── Connection Management ────────────────────────────────────────

@router.get("/connection", response_model=Optional[MS365ConnectionResponse])
async def get_connection(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    conn = await connection_client.get_by_user(current_user["user_id"], forward_headers=request.headers)
    if not conn:
        return None
    return conn


@router.delete("/connection", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    conn = await connection_client.get_by_user(current_user["user_id"], forward_headers=request.headers)
    if not conn:
        raise HTTPException(status_code=404, detail="No MS365 connection found")
    await connection_client.delete(conn["id"], forward_headers=request.headers)
    logger.info("ms365_disconnected", user_id=current_user["user_id"])


# ── Sync ─────────────────────────────────────────────────────────

@router.post("/sync", response_model=SyncStatusResponse)
async def force_sync(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Force an immediate sync — orchestrated here, CRUD via backend."""
    conn = await connection_client.get_by_user(current_user["user_id"], forward_headers=request.headers)
    if not conn or not conn.get("is_active"):
        raise HTTPException(status_code=404, detail="No active MS365 connection")

    # Fetch full connection detail with tokens if available via the detail endpoint
    full_conn = await connection_client.get(conn["id"], forward_headers=request.headers)
    if full_conn:
        conn = full_conn

    sync_service = MS365SyncService(request.headers)
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
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    folder: Optional[str] = None,
    search: Optional[str] = None,
    smart_label: Optional[str] = None,
    linked_contact_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    data = await email_crud_client.list(
        current_user["user_id"], skip, limit, folder, search, smart_label, linked_contact_id,
        forward_headers=request.headers,
    )
    return data


@router.get("/emails/{email_id}", response_model=SyncedEmailResponse)
async def get_email(
    email_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    email = await email_crud_client.get(email_id, current_user["user_id"], forward_headers=request.headers)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email


@router.post("/emails/{email_id}/ai-insights", response_model=EmailAiInsightResponse)
async def generate_email_ai_insights(
    email_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Generate AI insights — business logic stays in B4F."""
    email = await email_crud_client.get(email_id, current_user["user_id"], forward_headers=request.headers)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    content = email.get("body_html") or email.get("body_preview") or email.get("subject")

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

    user_prompt = f"Subject: {email.get('subject')}\nSender: {email.get('from_name')} ({email.get('from_address')})\nContent:\n{content}"

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
    send_request: SendEmailRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Compose and send via MS Graph — business logic stays in B4F."""
    conn = await connection_client.get_by_user(current_user["user_id"], forward_headers=request.headers)
    if not conn or not conn.get("is_active"):
        raise HTTPException(status_code=400, detail="No active MS365 connection.")

    try:
        expires_at = _parse_token_expiry(conn.get("token_expires_at"))
        access_token, new_data = await graph_service.ensure_valid_token(
            conn.get("access_token"), conn.get("refresh_token"), expires_at
        )
        if new_data:
            await connection_client.update(conn["id"], new_data, forward_headers=request.headers)

        return await graph_service.send_mail(
            access_token=access_token,
            subject=send_request.subject,
            body_content=send_request.body_content,
            to_recipients=send_request.to_recipients,
            cc_recipients=send_request.cc_recipients,
            bcc_recipients=send_request.bcc_recipients,
            body_type=send_request.body_type,
        )
    except HTTPException:
        raise
    except Exception as e:
        await connection_client.update(conn["id"], {"is_active": False, "connection_status": "token_expired"}, forward_headers=request.headers)
        logger.error("ms365_send_email_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emails/{email_id}/reply")
async def reply_email(
    email_id: str,
    reply_request: ReplyEmailRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    conn = await connection_client.get_by_user(current_user["user_id"], forward_headers=request.headers)
    if not conn or not conn.get("is_active"):
        raise HTTPException(status_code=400, detail="No active MS365 connection.")

    email = await email_crud_client.get(email_id, current_user["user_id"], forward_headers=request.headers)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found.")

    try:
        expires_at = _parse_token_expiry(conn.get("token_expires_at"))
        access_token, new_data = await graph_service.ensure_valid_token(
            conn.get("access_token"), conn.get("refresh_token"), expires_at
        )
        if new_data:
            await connection_client.update(conn["id"], new_data, forward_headers=request.headers)

        return await graph_service.reply_mail(
            access_token=access_token,
            message_id=email["ms_message_id"],
            comment=reply_request.comment,
            reply_all=reply_request.reply_all,
        )
    except HTTPException:
        raise
    except Exception as e:
        await connection_client.update(conn["id"], {"is_active": False, "connection_status": "token_expired"}, forward_headers=request.headers)
        logger.error("ms365_reply_email_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emails/{email_id}/forward")
async def forward_email(
    email_id: str,
    fwd_request: ForwardEmailRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    conn = await connection_client.get_by_user(current_user["user_id"], forward_headers=request.headers)
    if not conn or not conn.get("is_active"):
        raise HTTPException(status_code=400, detail="No active MS365 connection.")

    email = await email_crud_client.get(email_id, current_user["user_id"], forward_headers=request.headers)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found.")

    try:
        expires_at = _parse_token_expiry(conn.get("token_expires_at"))
        access_token, new_data = await graph_service.ensure_valid_token(
            conn.get("access_token"), conn.get("refresh_token"), expires_at
        )
        if new_data:
            await connection_client.update(conn["id"], new_data, forward_headers=request.headers)

        return await graph_service.forward_mail(
            access_token=access_token,
            message_id=email["ms_message_id"],
            to_recipients=fwd_request.to_recipients,
            comment=fwd_request.comment,
        )
    except HTTPException:
        raise
    except Exception as e:
        await connection_client.update(conn["id"], {"is_active": False, "connection_status": "token_expired"}, forward_headers=request.headers)
        logger.error("ms365_forward_email_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ── Calendar Events ──────────────────────────────────────────────

@router.get("/events", response_model=SyncedEventListResponse)
async def list_events(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user),
):
    data = await event_crud_client.list(
        current_user["user_id"], skip, limit, from_date, to_date,
        forward_headers=request.headers,
    )
    return data


@router.get("/events/{event_id}", response_model=SyncedEventResponse)
async def get_event(
    event_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    event = await event_crud_client.get(event_id, current_user["user_id"], forward_headers=request.headers)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


# ── Webhook Endpoint ─────────────────────────────────────────────

@router.post("/webhook")
async def ms365_webhook(
    request: Request,
):
    """Receive MS Graph change notifications — business logic stays in B4F."""
    params = request.query_params
    validation_token = params.get("validationToken")
    if validation_token:
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=validation_token, status_code=200)

    body = await request.json()
    notifications = body.get("value", [])

    if not notifications:
        return {"status": "ok"}

    for n in notifications:
        if n.get("clientState") != os.environ.get("WEBHOOK_API_KEY", ""):
            logger.warning("ms365_webhook_invalid_client_state")
            raise HTTPException(status_code=403, detail="Invalid client state")

    sync_service = MS365SyncService(request.headers)
    asyncio.ensure_future(sync_service.handle_webhook_notification(notifications))

    return {"status": "ok"}
