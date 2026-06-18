"""Pipedream provider routes.

Pipedream is the active integration provider. Local email/event storage still
uses the existing membrane_* tables until a dedicated data migration renames
those tables safely.
"""

import hashlib
import hmac
import json
import os
from datetime import datetime
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from shared.config import get_settings

from app.application.services.membrane_tenant_key_service import (
    build_tenant_key as _build_external_user_id,
    default_scope_for as _default_scope_for,
)
from app.infrastructure.clients_email_backend import integration_settings_client
from app.infrastructure.external.pipedream_service import (
    PipedreamClient,
    set_pipedream_credentials,
    _get_settings as _get_pipedream_settings,
)
from app.middleware.auth import get_current_user, require_super_admin
from app.presentation.schemas.provider_pipedream_schemas import (
    PipedreamActionRunRequest,
    PipedreamActionRunResponse,
    PipedreamConfigRequest,
    PipedreamConfigResponse,
    PipedreamConnectionListResponse,
    PipedreamConnectionResponse,
    PipedreamConnectUrlResponse,
    PipedreamIntegrationListResponse,
    PipedreamIntegrationResponse,
    PipedreamTokenRequest,
    PipedreamTokenResponse,
    PipedreamWebhookPayload,
)

logger = structlog.get_logger(__name__)
settings = get_settings("email-backend")
router = APIRouter(prefix="/api/v1/provider/pipedream")

_APP_SLUG_ALIASES = {
    "microsoft-outlook": "microsoft_outlook",
    "google-drive": "google_drive",
    "google-sheets": "google_sheets",
    "zoho-crm": "zoho_crm",
    "dynamics-crm": "microsoft_dynamics_365",
}


def _pipedream_app_slug(integration_key: str) -> str:
    key = (integration_key or "").replace("~connector.", "").strip()
    return _APP_SLUG_ALIASES.get(key, key.replace("-", "_"))


def _integration_key_from_app_slug(app_slug: str) -> str:
    return (app_slug or "").replace("_", "-")


async def _resolve_external_user_id(
    user: dict,
    integration_key: str,
    request_headers=None,
) -> str:
    tenant_id = user.get("tenant_id") or "default"
    user_id = user["user_id"]
    org_id = user.get("active_organization_id")

    try:
        setting = await integration_settings_client.get(integration_key, forward_headers=request_headers)
        if setting:
            scope = setting.get("scope_mode", _default_scope_for(integration_key))
            return _build_external_user_id(tenant_id, scope, user_id, org_id)
    except Exception as exc:
        logger.warning(
            "integration_setting_lookup_failed",
            provider="pipedream",
            integration_key=integration_key,
            tenant_id=tenant_id,
            error=str(exc),
        )

    return _build_external_user_id(tenant_id, _default_scope_for(integration_key), user_id, org_id)


def _with_app_param(connect_link_url: str, app: str) -> str:
    parts = urlsplit(connect_link_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["app"] = app
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _normalize_account(raw: dict[str, Any]) -> dict[str, Any]:
    app = raw.get("app") or {}
    return {
        "id": raw.get("id"),
        "app": app.get("name_slug"),
        "name": raw.get("name") or app.get("name"),
        "healthy": bool(raw.get("healthy", True)),
        "dead": raw.get("dead"),
        "created_at": raw.get("created_at"),
        "updated_at": raw.get("updated_at"),
    }


@router.post("/token", response_model=PipedreamTokenResponse)
async def create_pipedream_token(
    payload: PipedreamTokenRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    integration_key = payload.integration_key or payload.app or ""
    external_user_id = await _resolve_external_user_id(current_user, integration_key, request.headers)
    try:
        client = PipedreamClient()
        token_payload = await client.create_connect_token(
            external_user_id,
            allowed_origins=payload.allowed_origins,
            success_redirect_uri=payload.success_redirect_uri,
            error_redirect_uri=payload.error_redirect_uri,
            webhook_uri=payload.webhook_uri,
        )
        return PipedreamTokenResponse(
            token=token_payload["token"],
            expires_at=token_payload["expires_at"],
            connect_link_url=token_payload["connect_link_url"],
        )
    except httpx.HTTPStatusError as exc:
        logger.error("pipedream_token_error", status=exc.response.status_code, detail=exc.response.text[:300])
        raise HTTPException(status_code=502, detail="Failed to create Pipedream Connect token")
    except RuntimeError as exc:
        logger.error("pipedream_token_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Pipedream integration not configured")
    finally:
        if "client" in locals():
            await client.close()


@router.get("/connect-url", response_model=PipedreamConnectUrlResponse)
async def get_connect_url(
    integration_key: str,
    redirect_uri: Optional[str] = None,
    request: Request = None,
    current_user: dict = Depends(get_current_user),
):
    app = _pipedream_app_slug(integration_key)
    if not redirect_uri:
        ingress = os.environ.get("INGRESS_URL", "http://localhost:4700").rstrip("/")
        redirect_uri = f"{ingress}/settings/integrations?pipedream=connected&integration={integration_key}"
    external_user_id = await _resolve_external_user_id(
        current_user,
        integration_key,
        request.headers if request else None,
    )
    try:
        client = PipedreamClient()
        token_payload = await client.create_connect_token(
            external_user_id,
            success_redirect_uri=redirect_uri,
            error_redirect_uri=redirect_uri,
        )
        return PipedreamConnectUrlResponse(
            url=_with_app_param(token_payload["connect_link_url"], app),
            app=app,
        )
    except httpx.HTTPStatusError as exc:
        logger.error("pipedream_connect_url_error", status=exc.response.status_code, detail=exc.response.text[:300])
        raise HTTPException(status_code=502, detail="Failed to create Pipedream Connect Link")
    except RuntimeError as exc:
        logger.error("pipedream_connect_url_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Pipedream integration not configured")
    finally:
        if "client" in locals():
            await client.close()


@router.get("/connections", response_model=PipedreamConnectionListResponse)
async def list_connections(
    request: Request,
    integration_key: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    external_user_id = await _resolve_external_user_id(current_user, integration_key or "", request.headers)
    app = _pipedream_app_slug(integration_key) if integration_key else None
    try:
        client = PipedreamClient()
        accounts = await client.list_accounts(external_user_id, app=app)
        return PipedreamConnectionListResponse(
            items=[PipedreamConnectionResponse.model_validate(_normalize_account(account)) for account in accounts]
        )
    except httpx.HTTPStatusError as exc:
        logger.error("pipedream_list_connections_error", status=exc.response.status_code, detail=exc.response.text[:300])
        raise HTTPException(status_code=502, detail="Failed to fetch Pipedream connections")
    except RuntimeError as exc:
        logger.error("pipedream_list_connections_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Pipedream integration not configured")
    finally:
        if "client" in locals():
            await client.close()


@router.delete("/connections/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        client = PipedreamClient()
        removed = await client.delete_account(connection_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Connection not found")
    except httpx.HTTPStatusError as exc:
        logger.error("pipedream_delete_connection_error", status=exc.response.status_code, detail=exc.response.text[:300])
        raise HTTPException(status_code=502, detail="Failed to delete Pipedream connection")
    except RuntimeError as exc:
        logger.error("pipedream_delete_connection_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Pipedream integration not configured")
    finally:
        if "client" in locals():
            await client.close()


@router.get("/integrations", response_model=PipedreamIntegrationListResponse)
async def list_integrations(
    q: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    try:
        client = PipedreamClient()
        apps = await client.list_apps(query=q)
        return PipedreamIntegrationListResponse(items=[
            PipedreamIntegrationResponse(
                id=app.get("id") or app.get("name_slug"),
                key=_integration_key_from_app_slug(app.get("name_slug")),
                name=app.get("name") or app.get("name_slug"),
                description=app.get("description"),
                iconUrl=app.get("img_src"),
            )
            for app in apps
            if app.get("name_slug")
        ])
    except httpx.HTTPStatusError as exc:
        logger.error("pipedream_list_apps_error", status=exc.response.status_code, detail=exc.response.text[:300])
        raise HTTPException(status_code=502, detail="Failed to fetch Pipedream apps")
    except RuntimeError as exc:
        logger.error("pipedream_list_apps_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Pipedream integration not configured")
    finally:
        if "client" in locals():
            await client.close()


@router.post("/actions/{action_key}/run", response_model=PipedreamActionRunResponse)
async def run_action(
    action_key: str,
    body: PipedreamActionRunRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    integration_key = body.input.get("integration_key") or body.input.get("app") or action_key
    external_user_id = await _resolve_external_user_id(current_user, str(integration_key), request.headers)
    try:
        client = PipedreamClient()
        result = await client.run_action(
            action_id=body.action_key or action_key,
            external_user_id=external_user_id,
            configured_props=body.input,
            version=body.version,
            dynamic_props_id=body.dynamic_props_id,
            stash_id=body.stash_id,
        )
        return PipedreamActionRunResponse(success=True, output=result)
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:300] or "Action execution failed"
        logger.error("pipedream_action_run_error", action_key=action_key, status=exc.response.status_code, detail=detail)
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    except RuntimeError as exc:
        logger.error("pipedream_action_run_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Pipedream integration not configured")
    finally:
        if "client" in locals():
            await client.close()


def _verify_pipedream_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    secret = getattr(settings, "pipedream_webhook_secret", None)
    if not secret:
        logger.warning("pipedream_webhook_signature_skipped", reason="no_secret_configured")
        return True
    if not signature_header:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    received = signature_header.split("=", 1)[-1].strip()
    return hmac.compare_digest(expected, received)


@router.post("/webhook")
async def pipedream_webhook(request: Request):
    raw_body = await request.body()
    signature = (
        request.headers.get("x-pipedream-signature")
        or request.headers.get("x-signature")
        or request.headers.get("X-Signature")
    )
    if not _verify_pipedream_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = PipedreamWebhookPayload.model_validate(json.loads(raw_body))
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("pipedream_webhook_invalid_payload", error=str(exc))
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    logger.info(
        "pipedream_webhook_received",
        event_type=payload.event_type or payload.type,
        external_user_id=payload.external_user_id,
        app=payload.app,
    )
    return {"status": "ok"}


@router.get("/connections/by-user/{user_id}")
async def proxy_get_connection_by_user(
    user_id: str,
    request: Request,
    integration_key: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    from app.infrastructure.clients_email_backend import membrane_crud_client

    data = await membrane_crud_client.get_connection_by_user(
        user_id, integration_key=integration_key, forward_headers=request.headers,
    )
    if not data:
        raise HTTPException(status_code=404, detail="Connection not found")
    data["connection_provider"] = "pipedream"
    return data


@router.get("/emails")
async def proxy_list_emails(
    request: Request,
    user_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    folder: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    from app.infrastructure.clients_email_backend import membrane_crud_client

    return await membrane_crud_client.list_emails(
        user_id, skip=skip, limit=limit, folder=folder, search=search,
        forward_headers=request.headers,
    )


@router.get("/events")
async def proxy_list_events(
    request: Request,
    user_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user),
):
    from app.infrastructure.clients_email_backend import membrane_crud_client

    return await membrane_crud_client.list_events(
        user_id,
        skip=skip,
        limit=limit,
        from_date=from_date.isoformat() if from_date else None,
        to_date=to_date.isoformat() if to_date else None,
        forward_headers=request.headers,
    )


@router.post("/emails/send")
async def proxy_send_email(request: Request, current_user: dict = Depends(get_current_user)):
    action_id = os.environ.get("PIPEDREAM_SEND_EMAIL_ACTION_ID")
    if not action_id:
        raise HTTPException(status_code=501, detail="Pipedream send-email action is not configured")
    body = await request.json()
    return await run_action(action_id, PipedreamActionRunRequest(input=body), request, current_user)


@router.get("/emails/{email_id}")
async def proxy_get_email(
    email_id: str,
    request: Request,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    from app.infrastructure.clients_email_backend import membrane_crud_client

    data = await membrane_crud_client.get_email(email_id, user_id, forward_headers=request.headers)
    if not data:
        raise HTTPException(status_code=404, detail="Email not found")
    return data


@router.get("/events/{event_id}")
async def proxy_get_event(
    event_id: str,
    request: Request,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    from app.infrastructure.clients_email_backend import membrane_crud_client

    data = await membrane_crud_client.get_event(event_id, user_id, forward_headers=request.headers)
    if not data:
        raise HTTPException(status_code=404, detail="Event not found")
    return data


@router.post("/emails/{email_id}/reply")
async def proxy_reply_email(email_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    action_id = os.environ.get("PIPEDREAM_REPLY_EMAIL_ACTION_ID")
    if not action_id:
        raise HTTPException(status_code=501, detail="Pipedream reply-email action is not configured")
    body = await request.json()
    body["email_id"] = email_id
    return await run_action(action_id, PipedreamActionRunRequest(input=body), request, current_user)


@router.post("/emails/{email_id}/forward")
async def proxy_forward_email(email_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    action_id = os.environ.get("PIPEDREAM_FORWARD_EMAIL_ACTION_ID")
    if not action_id:
        raise HTTPException(status_code=501, detail="Pipedream forward-email action is not configured")
    body = await request.json()
    body["email_id"] = email_id
    return await run_action(action_id, PipedreamActionRunRequest(input=body), request, current_user)


@router.post("/sync-emails")
async def trigger_pipedream_sync(
    current_user: dict = Depends(get_current_user),
):
    action_id = os.environ.get("PIPEDREAM_SYNC_EMAILS_ACTION_ID")
    if not action_id:
        return {"status": "skipped", "synced": 0, "fetched": 0, "errors": ["Pipedream sync action is not configured"]}
    return await run_action(action_id, PipedreamActionRunRequest(input={}), Request({"type": "http", "headers": []}), current_user)


@router.get("/config", response_model=PipedreamConfigResponse)
async def get_pipedream_config(current_user: dict = Depends(get_current_user)):
    current = _get_pipedream_settings()
    has_secret = bool(current.pipedream_client_secret)
    return PipedreamConfigResponse(
        client_id=current.pipedream_client_id or "",
        project_id=current.pipedream_project_id or "",
        environment=current.pipedream_environment,
        api_url=current.pipedream_api_url,
        configured=bool(current.pipedream_client_id and has_secret and current.pipedream_project_id),
        secret_configured=has_secret,
    )


@router.put("/config", response_model=PipedreamConfigResponse)
async def update_pipedream_config(
    request: PipedreamConfigRequest,
    current_user: dict = Depends(require_super_admin),
):
    current = _get_pipedream_settings()
    incoming_secret = (request.client_secret or "").strip()
    is_masked = incoming_secret and set(incoming_secret) <= {"*", " "}
    effective_secret = current.pipedream_client_secret if not incoming_secret or is_masked else incoming_secret

    set_pipedream_credentials(
        client_id=request.client_id,
        client_secret=effective_secret,
        project_id=request.project_id,
        environment=request.environment,
        api_url=request.api_url,
    )
    return PipedreamConfigResponse(
        client_id=request.client_id,
        project_id=request.project_id,
        environment=request.environment,
        api_url=request.api_url,
        configured=bool(request.client_id and effective_secret and request.project_id),
        secret_configured=bool(effective_secret),
        message="Pipedream configuration updated successfully",
    )
