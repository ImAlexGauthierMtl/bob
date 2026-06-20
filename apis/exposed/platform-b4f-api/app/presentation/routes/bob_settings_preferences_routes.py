"""Bob conversation and voice settings managed locally by CDE."""

from __future__ import annotations

import os
import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status


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

_RUNTIME_DEFAULTS: dict[str, Any] = {
    "providers": [
        {
            "id": "fireworks-kimi",
            "name": "Fireworks Kimi K2.7 Code",
            "provider": "fireworks",
            "model": "accounts/fireworks/models/kimi-k2p7-code",
            "status": "runtime_backend_managed",
            "enabled": True,
        },
        {
            "id": "local-runtime",
            "name": "Bob Local Runtime",
            "provider": "local",
            "model": "bob-local-runtime",
            "status": "dev_fallback",
            "enabled": True,
        },
    ],
    "active_provider": "auto",
    "agents": [
        {
            "id": "agent-bob-orchestrator",
            "name": "Bob Orchestrator",
            "description": "Agent principal CDE pour conversation, memoire et appels outils controles.",
            "provider_id": "fireworks-kimi",
            "status": "active",
            "skills": ["skill-routing", "skill-memory"],
            "tools": ["tool-runtime-status", "tool-memory-summary"],
        }
    ],
    "skills": [
        {
            "id": "skill-routing",
            "name": "Tool Routing",
            "description": "Selectionne les familles d'outils exposees au run selon le contexte.",
            "status": "active",
            "scope": "shared_clean",
        },
        {
            "id": "skill-memory",
            "name": "Memory Readback",
            "description": "Resume et verifie la memoire privee et organisationnelle transmise par Bob Chat.",
            "status": "active",
            "scope": "shared_clean",
        },
    ],
    "tools": [
        {
            "id": "tool-runtime-status",
            "name": "bob_runtime_status",
            "family": "runtime",
            "risk": "read",
            "status": "active",
            "description": "Confirme l'etat runtime, les droits et les familles d'outils disponibles.",
        },
        {
            "id": "tool-memory-summary",
            "name": "bob_memory_context_summary",
            "family": "memory",
            "risk": "read",
            "status": "active",
            "description": "Resume le contexte memoire deja fourni au runtime.",
        },
    ],
    "memory": {
        "private_user": "tenant_id + user_id obligatoire",
        "organization": "promotion humaine avant usage durable",
        "rag": "Postgres source de verite, Milvus reconstructible",
        "vector_index": "ACL revalidees apres recherche vectorielle",
    },
    "source": "cde-local",
}

_CONVERSATION_SETTINGS_BY_ACTOR: dict[str, dict[str, Any]] = {}
_VOICE_SETTINGS_BY_ACTOR: dict[str, dict[str, Any]] = {}
_RUNTIME_SETTINGS_BY_ACTOR: dict[str, dict[str, Any]] = {}
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
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict[str, Any]:
    settings = _runtime_settings_for_actor(_actor_key_from_authorization(authorization))
    return deepcopy(settings)


@router.post("/runtime/agents", status_code=status.HTTP_201_CREATED)
async def create_runtime_agent(
    payload: dict[str, Any],
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    principal: LocalSettingsPrincipal = Depends(_require_settings_mutation_permission),
) -> dict[str, Any]:
    return _append_runtime_item(
        scope="runtime-agent",
        collection="agents",
        payload=payload,
        principal=principal,
        idempotency_key=idempotency_key,
        defaults={
            "description": "",
            "provider_id": "fireworks-kimi",
            "status": "draft",
            "skills": [],
            "tools": [],
        },
    )


@router.post("/runtime/skills", status_code=status.HTTP_201_CREATED)
async def create_runtime_skill(
    payload: dict[str, Any],
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    principal: LocalSettingsPrincipal = Depends(_require_settings_mutation_permission),
) -> dict[str, Any]:
    return _append_runtime_item(
        scope="runtime-skill",
        collection="skills",
        payload=payload,
        principal=principal,
        idempotency_key=idempotency_key,
        defaults={
            "description": "",
            "status": "draft",
            "scope": "shared_clean",
        },
    )


@router.post("/runtime/tools", status_code=status.HTTP_201_CREATED)
async def create_runtime_tool(
    payload: dict[str, Any],
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    principal: LocalSettingsPrincipal = Depends(_require_settings_mutation_permission),
) -> dict[str, Any]:
    return _append_runtime_item(
        scope="runtime-tool",
        collection="tools",
        payload=payload,
        principal=principal,
        idempotency_key=idempotency_key,
        defaults={
            "description": "",
            "family": "custom",
            "risk": "read",
            "status": "draft",
        },
    )


def _clean_dict(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _runtime_settings_for_actor(actor_key: str) -> dict[str, Any]:
    settings = _settings_for_actor(
        _RUNTIME_SETTINGS_BY_ACTOR,
        _RUNTIME_DEFAULTS,
        actor_key,
    )
    settings["active_provider"] = os.environ.get("AGENT_RUNTIME_PROVIDER", settings["active_provider"])
    return settings


def _append_runtime_item(
    *,
    scope: str,
    collection: str,
    payload: dict[str, Any],
    principal: LocalSettingsPrincipal,
    idempotency_key: str,
    defaults: dict[str, Any],
) -> dict[str, Any]:
    replay = _get_idempotency_replay(scope, principal, idempotency_key, payload)
    if replay:
        return replay

    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "name_required"},
        )

    settings = _runtime_settings_for_actor(principal.actor_key)
    item = {
        "id": str(payload.get("id") or f"{collection[:-1]}-{uuid4().hex[:10]}"),
        "name": name,
        **defaults,
        **_clean_dict(payload),
    }
    settings[collection].append(item)
    response = {"item": deepcopy(item), "runtime": deepcopy(settings)}
    _store_idempotency_replay(scope, principal, idempotency_key, payload, response)
    return response
