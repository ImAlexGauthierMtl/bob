"""Bob conversation and voice settings managed locally by CDE."""

from __future__ import annotations

import os
import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

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


def _clean_dict(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}
