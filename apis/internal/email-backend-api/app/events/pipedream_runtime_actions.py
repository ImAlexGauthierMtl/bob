"""Event-bus handler for Bob runtime Pipedream read actions."""

from __future__ import annotations

import json
from typing import Any

import structlog
from shared.event_bus import Event, event_bus

from app.application.services.membrane_tenant_key_service import build_tenant_key, default_scope_for
from app.application.use_cases.pipedream_provider_use_cases import PipedreamProviderUseCases
from app.infrastructure.clients_email_backend import integration_settings_client
from app.infrastructure.external.pipedream_service import (
    PipedreamClient,
    _get_settings as get_pipedream_settings,
    set_pipedream_credentials,
)


EVENT_TYPE = "agent-runtime.pipedream.read.requested"

logger = structlog.get_logger(__name__)
_registered = False


def register_pipedream_runtime_action_subscriber() -> None:
    """Register the email-owned Pipedream executor on the shared event bus."""

    global _registered
    if _registered:
        return
    event_bus.subscribe(EVENT_TYPE, handle_pipedream_runtime_action_request)
    _registered = True


async def handle_pipedream_runtime_action_request(event: Event) -> None:
    payload = event.payload if isinstance(event.payload, dict) else {}
    request_id = str(payload.get("request_id") or "")
    response_key = str(payload.get("response_key") or "")
    if not response_key:
        logger.warning("pipedream_runtime_action_missing_response_key", request_id=request_id)
        return

    try:
        data = await _execute_request(payload)
        envelope = {"ok": True, "request_id": request_id, "data": data}
    except Exception as exc:
        logger.exception("pipedream_runtime_action_failed", request_id=request_id, error=str(exc))
        envelope = {
            "ok": False,
            "request_id": request_id,
            "code": "pipedream_provider_event_error",
            "detail": {"error": str(exc)[:400]},
        }
    await _write_response(response_key, envelope)


async def _execute_request(payload: dict[str, Any]) -> dict[str, Any]:
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    user = _user_from_context(context)
    operation = str(payload.get("operation") or "")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    use_cases = _runtime_use_cases(user["tenant_id"])

    if operation == "list_connections":
        return {"items": await use_cases.list_connections(user, None, None)}

    if operation == "run_action":
        action_key = str(data.get("action_key") or "")
        configured_props = data.get("input") if isinstance(data.get("input"), dict) else {}
        integration_key = str(
            data.get("integration_key")
            or configured_props.get("integration_key")
            or configured_props.get("app")
            or action_key
        )
        output = await use_cases.run_action(
            user,
            action_key,
            integration_key,
            configured_props,
            None,
        )
        return {"success": True, "output": output}

    raise ValueError(f"Unsupported Pipedream runtime operation: {operation}")


def _runtime_use_cases(tenant_id: str) -> PipedreamProviderUseCases:
    async def setting_lookup(integration_key: str, _request_headers: Any = None):
        return await integration_settings_client.get(integration_key, tenant_id=tenant_id)

    return PipedreamProviderUseCases(
        client_factory=PipedreamClient,
        setting_lookup=setting_lookup,
        build_external_user_id=build_tenant_key,
        default_scope_for=default_scope_for,
        get_settings=get_pipedream_settings,
        set_credentials=set_pipedream_credentials,
    )


def _user_from_context(context: dict[str, Any]) -> dict[str, Any]:
    roles = context.get("roles") if isinstance(context.get("roles"), list) else []
    role = next((str(item) for item in roles if item), "admin")
    return {
        "user_id": str(context.get("user_id") or "system"),
        "email": str(context.get("email") or "system"),
        "tenant_id": str(context.get("tenant_id") or "default"),
        "role": role,
        "is_super_admin": role == "super_admin",
    }


async def _write_response(response_key: str, envelope: dict[str, Any]) -> None:
    if not hasattr(event_bus, "_get_redis"):
        logger.warning("pipedream_runtime_action_no_response_store", response_key=response_key)
        return
    redis = await event_bus._get_redis()
    await redis.set(response_key, json.dumps(envelope), ex=90)
