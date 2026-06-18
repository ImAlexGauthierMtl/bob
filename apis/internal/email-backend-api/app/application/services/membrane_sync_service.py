"""Membrane Sync Service — pulls emails from Membrane via the MS Graph proxy.

This implements Option C (hybrid): we don't rely on Membrane Flow webhooks to
populate the local DB; instead we actively pull recent messages through the
Membrane connection proxy and upsert them into the local
`membrane_synced_emails` table.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

from app.infrastructure.external.membrane_service import (
    generate_membrane_token,
    MembraneClient,
)
from app.infrastructure.clients_email_backend import membrane_crud_client

logger = structlog.get_logger(__name__)


def _graph_msg_to_upsert(msg: Dict[str, Any], local_connection_id: str, user_id: str, provider: str) -> Dict[str, Any]:
    """Transform a raw MS Graph message into MembraneEmailUpsert-compatible dict."""
    from_obj = (msg.get("from") or {}).get("emailAddress") or {}
    to_list = [
        {
            "address": (r.get("emailAddress") or {}).get("address", ""),
            "name": (r.get("emailAddress") or {}).get("name", ""),
        }
        for r in msg.get("toRecipients") or []
    ]
    cc_list = [
        {
            "address": (r.get("emailAddress") or {}).get("address", ""),
            "name": (r.get("emailAddress") or {}).get("name", ""),
        }
        for r in msg.get("ccRecipients") or []
    ]

    body = msg.get("body") or {}
    body_html = body.get("content") if body.get("contentType", "").lower() == "html" else None
    body_preview = msg.get("bodyPreview") or (body.get("content") if not body_html else None)

    received = msg.get("receivedDateTime")

    return {
        "membrane_connection_id": local_connection_id,
        "user_id": user_id,
        "provider_message_id": msg.get("id"),
        "provider": provider,
        "subject": msg.get("subject"),
        "body_preview": body_preview,
        "body_html": body_html,
        "from_address": from_obj.get("address"),
        "from_name": from_obj.get("name"),
        "to_addresses": to_list if to_list else None,
        "cc_addresses": cc_list if cc_list else None,
        "received_at": received,
        "is_read": bool(msg.get("isRead", False)),
        "importance": msg.get("importance", "normal"),
        "has_attachments": bool(msg.get("hasAttachments", False)),
        "attachments_meta": None,
        "folder": "inbox",
        "conversation_id": msg.get("conversationId"),
    }


async def sync_membrane_emails(
    user: dict,
    local_connection: dict,
    top: int = 50,
    forward_headers: Optional[dict] = None,
) -> Dict[str, Any]:
    """Pull recent messages via Membrane proxy and upsert into local DB.

    Parameters
    ----------
    user: dict
        The authenticated user (must contain `user_id`, `email`, `tenant_id`).
    local_connection: dict
        The membrane_connection row from email-backend-api (must contain
        `membrane_connection_id` and `id`).
    top: int
        Number of recent messages to pull (Graph `$top` parameter).

    Returns
    -------
    dict with `synced` count and optional `errors` list.
    """
    from app.presentation.routes.provider_membrane_routes import _build_tenant_key, _default_scope_for
    tenant_key = _build_tenant_key(
        user.get("tenant_id", "default"),
        _default_scope_for(local_connection.get("integration_key", "")),
        user["user_id"],
        user.get("active_organization_id"),
    )
    token = generate_membrane_token(
        tenant_key=tenant_key,
        name=user.get("email", tenant_key),
        fields={"croo_user_id": user["user_id"]},
        expires_minutes=10,
    )
    client = MembraneClient(token)

    membrane_connection_id = local_connection.get("membrane_connection_id")
    local_connection_id = local_connection.get("id")
    provider = local_connection.get("integration_key") or "microsoft-outlook"

    synced = 0
    errors: List[str] = []

    try:
        # Fetch the latest `top` messages from the inbox
        # MS Graph: /me/messages with $top, $orderby
        data = await client.proxy_get(
            membrane_connection_id,
            "/me/messages",
            params={
                "$top": str(top),
                "$orderby": "receivedDateTime desc",
                "$select": "id,subject,bodyPreview,body,from,toRecipients,ccRecipients,receivedDateTime,isRead,importance,hasAttachments,conversationId",
            },
        )
        messages = data.get("value", [])

        for msg in messages:
            try:
                payload = _graph_msg_to_upsert(msg, local_connection_id, user["user_id"], provider)
                await membrane_crud_client.upsert_email(payload, forward_headers=forward_headers)
                synced += 1
            except Exception as exc:
                errors.append(f"{msg.get('id')}: {exc}")
                logger.warning("membrane_sync_email_upsert_failed", message_id=msg.get("id"), error=str(exc))

        logger.info(
            "membrane_sync_complete",
            user_id=user["user_id"],
            connection_id=membrane_connection_id,
            fetched=len(messages),
            synced=synced,
            error_count=len(errors),
        )
    except Exception as exc:
        logger.error("membrane_sync_failed", user_id=user["user_id"], error=str(exc))
        raise
    finally:
        await client.close()

    return {"synced": synced, "fetched": len(messages) if 'messages' in dir() else 0, "errors": errors}
