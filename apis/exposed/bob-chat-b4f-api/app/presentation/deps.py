"""Presentation dependencies for Bob Chat B4F."""

from __future__ import annotations

import os

from fastapi import HTTPException, status

from app.application.services.idempotency import InMemoryIdempotencyStore
from app.application.use_cases.bob_chat_use_cases import BobChatUseCases
from app.infrastructure.clients.agent_memory_client import AgentMemoryBackendClient
from app.infrastructure.clients.agent_runtime_client import AgentRuntimeBackendClient
from app.infrastructure.clients.bob_cloud_identity import BobCloudIdentityProvider
from app.infrastructure.clients.conversation_client import ConversationBackendClient
from shared.config import get_settings
from shared.infrastructure import InternalSessionContextSigner
from shared.services import BobCloudClient, BobCloudModeError, create_bob_cloud_client_from_env


settings = get_settings("bob-chat")
idempotency_store = InMemoryIdempotencyStore()


def get_bob_cloud_client() -> BobCloudClient:
    try:
        return create_bob_cloud_client_from_env()
    except BobCloudModeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "bob_cloud_unconfigured", "message": str(exc)},
        ) from exc


def get_internal_session_signer() -> InternalSessionContextSigner:
    environment = os.environ.get("ENV", os.environ.get("ENVIRONMENT", settings.environment)).lower()
    secret = os.environ.get("INTERNAL_SESSION_SECRET", "")
    if not secret and environment in {"development", "dev", "test", "ci"}:
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


def get_bob_chat_use_cases() -> BobChatUseCases:
    bob_cloud_client = get_bob_cloud_client()
    signer = get_internal_session_signer()
    return BobChatUseCases(
        identity_provider=BobCloudIdentityProvider(
            bob_cloud_client=bob_cloud_client,
            signer=signer,
        ),
        conversation_client=ConversationBackendClient(),
        runtime_client=AgentRuntimeBackendClient(),
        memory_client=AgentMemoryBackendClient(),
        idempotency_store=idempotency_store,
    )
