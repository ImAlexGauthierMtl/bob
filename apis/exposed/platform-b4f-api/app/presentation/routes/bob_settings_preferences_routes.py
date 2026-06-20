"""Bob conversation and voice settings managed locally by CDE."""

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.infrastructure.clients.platform_clients import agent_runtime_client
from shared.infrastructure import InternalSessionContext, InternalSessionContextSigner


router = APIRouter()


@dataclass(frozen=True)
class LocalSettingsPrincipal:
    actor_key: str
    capabilities: set[str]


_CONVERSATION_DEFAULTS: dict[str, Any] = {
    "personality": {
        "tone": "professional",
        "formality": 0.5,
        "response_length": "balanced",
        "language": "auto",
        "creativity": 0.3,
        "emoji_usage": False,
    },
    "available_tones": ["professional", "friendly", "direct", "playful"],
    "available_languages": [
        {"code": "auto", "name": "Auto-detect"},
        {"code": "fr", "name": "French"},
        {"code": "en", "name": "English"},
        {"code": "es", "name": "Spanish"},
    ],
    "source": "cde-local",
}

_VOICE_DEFAULTS: dict[str, Any] = {
    "voice": {
        "voice": "autumn",
        "speed": 1.0,
        "auto_listen": True,
    },
    "available_voices": [
        {
            "id": "autumn",
            "name": "Autumn",
            "gender": "female",
            "accent": "North American",
            "style": "Warm",
            "provider": "local",
        },
        {
            "id": "cedar",
            "name": "Cedar",
            "gender": "male",
            "accent": "North American",
            "style": "Calm",
            "provider": "local",
        },
        {
            "id": "marie",
            "name": "Marie",
            "gender": "female",
            "accent": "French Canadian",
            "style": "Clear",
            "provider": "local",
        },
    ],
    "source": "cde-local",
}

_CONVERSATION_SETTINGS_BY_ACTOR: dict[str, dict[str, Any]] = {}
_VOICE_SETTINGS_BY_ACTOR: dict[str, dict[str, Any]] = {}
_IDEMPOTENCY_REPLAYS: dict[tuple[str, str, str], dict[str, Any]] = {}


async def _require_settings_mutation_permission(
    authorization: str | None = Header(None, alias="Authorization"),
    x_cde_capabilities: str | None = Header(None, alias="X-CDE-Capabilities"),
) -> LocalSettingsPrincipal:
    if not _has_bearer_session(authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "session_required"},
        )

    capabilities = _capabilities_from_header_or_env(x_cde_capabilities)
    if "admin" not in capabilities and "bob_settings.manage" not in capabilities:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "capability_denied", "capability": "bob_settings.manage"},
        )
    return LocalSettingsPrincipal(
        actor_key=_actor_key_from_authorization(authorization),
        capabilities=capabilities,
    )


def _has_bearer_session(authorization: str | None) -> bool:
    if not authorization:
        return False
    parts = authorization.split(maxsplit=1)
    return len(parts) == 2 and parts[0].lower() == "bearer" and bool(parts[1].strip())


def _capabilities_from_header_or_env(x_cde_capabilities: str | None) -> set[str]:
    raw_capabilities = x_cde_capabilities
    if raw_capabilities is None:
        raw_capabilities = os.environ.get("CDE_LOCAL_BOB_SETTINGS_CAPABILITIES")
    if raw_capabilities is None and _is_development():
        raw_capabilities = "bob_settings.manage"
    return {
        capability.strip()
        for capability in (raw_capabilities or "").split(",")
        if capability.strip()
    }


def _is_development() -> bool:
    environment = os.environ.get("ENVIRONMENT", "development").strip().lower()
    return environment in {"development", "dev", "local"}


def _actor_key_from_authorization(authorization: str | None) -> str:
    if not _has_bearer_session(authorization):
        return "local-anonymous"
    token = authorization.split(maxsplit=1)[1].strip()
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"local-session:{digest}"


def _settings_for_actor(
    store: dict[str, dict[str, Any]],
    defaults: dict[str, Any],
    actor_key: str,
) -> dict[str, Any]:
    if actor_key not in store:
        store[actor_key] = deepcopy(defaults)
    return store[actor_key]


def _payload_fingerprint(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _get_idempotency_replay(
    scope: str,
    principal: LocalSettingsPrincipal,
    idempotency_key: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    replay_key = (principal.actor_key, scope, idempotency_key)
    replay = _IDEMPOTENCY_REPLAYS.get(replay_key)
    if not replay:
        return None
    if replay["fingerprint"] != _payload_fingerprint(payload):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "idempotency_conflict"},
        )
    return deepcopy(replay["response"])


def _store_idempotency_replay(
    scope: str,
    principal: LocalSettingsPrincipal,
    idempotency_key: str,
    payload: dict[str, Any],
    response: dict[str, Any],
) -> None:
    replay_key = (principal.actor_key, scope, idempotency_key)
    _IDEMPOTENCY_REPLAYS[replay_key] = {
        "fingerprint": _payload_fingerprint(payload),
        "response": deepcopy(response),
    }


@router.get("/conversation")
async def get_conversation_settings(
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict[str, Any]:
    settings = _settings_for_actor(
        _CONVERSATION_SETTINGS_BY_ACTOR,
        _CONVERSATION_DEFAULTS,
        _actor_key_from_authorization(authorization),
    )
    return deepcopy(settings)


@router.put("/conversation")
async def update_conversation_settings(
    payload: dict[str, Any],
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    principal: LocalSettingsPrincipal = Depends(_require_settings_mutation_permission),
) -> dict[str, Any]:
    replay = _get_idempotency_replay("conversation", principal, idempotency_key, payload)
    if replay:
        return replay

    settings = _settings_for_actor(
        _CONVERSATION_SETTINGS_BY_ACTOR,
        _CONVERSATION_DEFAULTS,
        principal.actor_key,
    )
    personality = payload.get("personality")
    if isinstance(personality, dict):
        settings["personality"].update(_clean_dict(personality))
    response = deepcopy(settings)
    _store_idempotency_replay("conversation", principal, idempotency_key, payload, response)
    return response


@router.get("/voice")
async def get_voice_settings(
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict[str, Any]:
    settings = _settings_for_actor(
        _VOICE_SETTINGS_BY_ACTOR,
        _VOICE_DEFAULTS,
        _actor_key_from_authorization(authorization),
    )
    return deepcopy(settings)


@router.put("/voice")
async def update_voice_settings(
    payload: dict[str, Any],
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    principal: LocalSettingsPrincipal = Depends(_require_settings_mutation_permission),
) -> dict[str, Any]:
    replay = _get_idempotency_replay("voice", principal, idempotency_key, payload)
    if replay:
        return replay

    settings = _settings_for_actor(
        _VOICE_SETTINGS_BY_ACTOR,
        _VOICE_DEFAULTS,
        principal.actor_key,
    )
    voice = payload.get("voice")
    if isinstance(voice, dict):
        settings["voice"].update(_clean_dict(voice))
    response = deepcopy(settings)
    _store_idempotency_replay("voice", principal, idempotency_key, payload, response)
    return response


@router.get("/runtime")
async def get_runtime_settings(
    request: Request,
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict[str, Any]:
    return await _runtime_backend_call(
        "get_settings",
        request=request,
        authorization=authorization,
        capabilities=set(),
    )


@router.post("/runtime/agents", status_code=status.HTTP_201_CREATED)
async def create_runtime_agent(
    payload: dict[str, Any],
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    principal: LocalSettingsPrincipal = Depends(_require_settings_mutation_permission),
) -> dict[str, Any]:
    return await _runtime_backend_call(
        "create_catalog_item",
        request=request,
        authorization=request.headers.get("authorization"),
        capabilities=principal.capabilities,
        collection="agents",
        payload=payload,
        idempotency_key=idempotency_key,
    )


@router.post("/runtime/skills", status_code=status.HTTP_201_CREATED)
async def create_runtime_skill(
    payload: dict[str, Any],
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    principal: LocalSettingsPrincipal = Depends(_require_settings_mutation_permission),
) -> dict[str, Any]:
    return await _runtime_backend_call(
        "create_catalog_item",
        request=request,
        authorization=request.headers.get("authorization"),
        capabilities=principal.capabilities,
        collection="skills",
        payload=payload,
        idempotency_key=idempotency_key,
    )


@router.post("/runtime/tools", status_code=status.HTTP_201_CREATED)
async def create_runtime_tool(
    payload: dict[str, Any],
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    principal: LocalSettingsPrincipal = Depends(_require_settings_mutation_permission),
) -> dict[str, Any]:
    return await _runtime_backend_call(
        "create_catalog_item",
        request=request,
        authorization=request.headers.get("authorization"),
        capabilities=principal.capabilities,
        collection="tools",
        payload=payload,
        idempotency_key=idempotency_key,
    )


def _clean_dict(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


async def _runtime_backend_call(
    method: str,
    *,
    request: Request,
    authorization: str | None,
    capabilities: set[str],
    collection: str | None = None,
    payload: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    headers = _runtime_backend_headers(
        request=request,
        authorization=authorization,
        capabilities=capabilities,
        idempotency_key=idempotency_key,
    )
    try:
        if method == "get_settings":
            return await agent_runtime_client.get_settings(headers=headers)
        if method == "create_catalog_item" and collection and payload is not None:
            return await agent_runtime_client.create_catalog_item(
                collection=collection,
                data=payload,
                headers=headers,
            )
    except httpx.HTTPStatusError as exc:
        detail = _safe_backend_detail(exc.response)
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "agent_runtime_backend_unavailable", "message": str(exc)},
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"code": "runtime_backend_call_invalid"},
    )


def _runtime_backend_headers(
    *,
    request: Request,
    authorization: str | None,
    capabilities: set[str],
    idempotency_key: str | None,
) -> dict[str, str]:
    trace_id = request.headers.get("x-trace-id") or hashlib.sha256(
        f"{authorization or 'anonymous'}:{request.url.path}".encode("utf-8")
    ).hexdigest()[:32]
    context = InternalSessionContext(
        tenant_id=request.headers.get("x-tenant-id") or "tenant-croo-local",
        user_id=_actor_key_from_authorization(authorization).replace(":", "-")[:64],
        session_id="bob-settings-local",
        trace_id=trace_id,
        permissions=tuple(sorted(capabilities)),
        entitlements=("bob_settings.manage",) if capabilities else (),
        roles=("admin",) if "admin" in capabilities else (),
    )
    headers = {
        "X-Session-Context": _internal_session_signer().issue(context),
        "X-Trace-Id": trace_id,
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _internal_session_signer() -> InternalSessionContextSigner:
    secret = os.environ.get("INTERNAL_SESSION_SECRET", "")
    if not secret and _is_development():
        secret = "dev-internal-session-secret-not-for-production"
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "internal_session_secret_missing"},
        )
    return InternalSessionContextSigner(
        secret,
        kid=os.environ.get("INTERNAL_SESSION_KID", "internal-session-dev"),
    )


def _safe_backend_detail(response: httpx.Response) -> Any:
    if not response.content:
        return {"code": "agent_runtime_backend_error"}
    try:
        payload = response.json()
    except ValueError:
        return {"code": "agent_runtime_backend_error", "message": response.text}
    return payload.get("detail", payload)
