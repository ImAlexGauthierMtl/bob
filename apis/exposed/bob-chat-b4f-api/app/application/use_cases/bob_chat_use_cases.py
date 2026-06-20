"""Bob Chat application use cases."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from typing import Any, Mapping, Protocol

from app.application.services.idempotency import (
    IdempotencyConflictError,
    InMemoryIdempotencyStore,
)
from app.domain import (
    BobChatError,
    BobChatMessageCommand,
    BobChatSecurityContext,
    ConversationSessionDraft,
)


class IdentityProviderPort(Protocol):
    async def resolve(
        self,
        *,
        forward_headers: Any,
        trace_id: str,
    ) -> BobChatSecurityContext:
        ...


class ConversationClientPort(Protocol):
    async def create_session(
        self,
        *,
        draft: ConversationSessionDraft,
        security_context: BobChatSecurityContext,
    ) -> dict[str, Any]:
        ...

    async def list_sessions(
        self,
        *,
        security_context: BobChatSecurityContext,
    ) -> dict[str, Any]:
        ...

    async def get_session(
        self,
        *,
        session_id: str,
        security_context: BobChatSecurityContext,
    ) -> dict[str, Any]:
        ...

    async def delete_session(
        self,
        *,
        session_id: str,
        security_context: BobChatSecurityContext,
    ) -> None:
        ...

    async def add_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        security_context: BobChatSecurityContext,
        idempotency_key: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        ...


class AgentRuntimeClientPort(Protocol):
    async def create_run(
        self,
        *,
        session_id: str,
        input_message_id: str,
        prompt: str,
        channel: str,
        metadata: Mapping[str, Any],
        security_context: BobChatSecurityContext,
        idempotency_key: str,
    ) -> dict[str, Any]:
        ...


class AgentMemoryClientPort(Protocol):
    async def build_context(
        self,
        *,
        query: str,
        security_context: BobChatSecurityContext,
    ) -> dict[str, Any]:
        ...


class BobChatUseCases:
    def __init__(
        self,
        *,
        identity_provider: IdentityProviderPort,
        conversation_client: ConversationClientPort,
        runtime_client: AgentRuntimeClientPort,
        memory_client: AgentMemoryClientPort,
        idempotency_store: InMemoryIdempotencyStore,
    ) -> None:
        self.identity_provider = identity_provider
        self.conversation_client = conversation_client
        self.runtime_client = runtime_client
        self.memory_client = memory_client
        self.idempotency_store = idempotency_store

    async def create_message(
        self,
        *,
        command: BobChatMessageCommand,
        idempotency_key: str,
        forward_headers: Any,
        trace_id: str,
    ) -> dict[str, Any]:
        security_context = await self.identity_provider.resolve(
            forward_headers=forward_headers,
            trace_id=trace_id,
        )
        payload_hash = _payload_hash(command)
        dedupe_key = (
            f"{security_context.tenant_id}:{security_context.user_id}:"
            f"POST:/api/bob-chat/v1/messages:{idempotency_key}"
        )

        try:
            existing_response = self.idempotency_store.get(dedupe_key, payload_hash)
        except IdempotencyConflictError as exc:
            raise BobChatError(
                "idempotency_conflict",
                status_code=409,
                detail={"code": "idempotency_conflict"},
            ) from exc
        if existing_response:
            return existing_response

        session = await self._ensure_session(command, security_context)
        user_message = await self.conversation_client.add_message(
            session_id=session["id"],
            role="user",
            content=command.message,
            security_context=security_context,
            idempotency_key=f"{idempotency_key}:user",
            metadata={
                "channel": command.channel,
                "client_context": command.client_context,
                "mission": _mission_payload(command),
            },
        )
        memory_context = await self.memory_client.build_context(
            query=command.message,
            security_context=security_context,
        )
        runtime_run = await self.runtime_client.create_run(
            session_id=session["id"],
            input_message_id=user_message["id"],
            prompt=command.message,
            channel=command.channel,
            metadata={
                "client_context": command.client_context,
                "agent_id": _agent_id_payload(command),
                "mission": _mission_payload(command),
                "memory_context": memory_context,
            },
            security_context=security_context,
            idempotency_key=f"{idempotency_key}:run",
        )
        assistant_message = await self.conversation_client.add_message(
            session_id=session["id"],
            role="assistant",
            content=runtime_run["assistant_content"],
            security_context=security_context,
            idempotency_key=f"{idempotency_key}:assistant",
            metadata={
                "source": "agent-runtime-backend-api",
                "run_id": runtime_run["id"],
                "mode": runtime_run["mode"],
            },
        )
        refreshed_session = await self.conversation_client.get_session(
            session_id=session["id"],
            security_context=security_context,
        )

        response = {
            "message": assistant_message,
            "input_message": user_message,
            "session": refreshed_session,
            "run": {
                "id": runtime_run["id"],
                "status": runtime_run["status"],
                "mode": runtime_run["mode"],
                "trace_id": runtime_run["trace_id"],
            },
            "actions": runtime_run.get("actions", []),
            "narration_steps": _public_narration_steps(runtime_run.get("narration_steps", [])),
            "artifacts": runtime_run.get("artifacts", []),
        }
        self.idempotency_store.store(dedupe_key, payload_hash, response)
        return response

    async def list_sessions(self, *, forward_headers: Any, trace_id: str) -> dict[str, Any]:
        security_context = await self.identity_provider.resolve(
            forward_headers=forward_headers,
            trace_id=trace_id,
        )
        return await self.conversation_client.list_sessions(security_context=security_context)

    async def get_session(
        self,
        *,
        session_id: str,
        forward_headers: Any,
        trace_id: str,
    ) -> dict[str, Any]:
        security_context = await self.identity_provider.resolve(
            forward_headers=forward_headers,
            trace_id=trace_id,
        )
        return await self.conversation_client.get_session(
            session_id=session_id,
            security_context=security_context,
        )

    async def delete_session(
        self,
        *,
        session_id: str,
        forward_headers: Any,
        trace_id: str,
    ) -> None:
        security_context = await self.identity_provider.resolve(
            forward_headers=forward_headers,
            trace_id=trace_id,
        )
        await self.conversation_client.delete_session(
            session_id=session_id,
            security_context=security_context,
        )

    async def _ensure_session(
        self,
        command: BobChatMessageCommand,
        security_context: BobChatSecurityContext,
    ) -> dict[str, Any]:
        if command.session_id:
            return await self.conversation_client.get_session(
                session_id=command.session_id,
                security_context=security_context,
            )

        return await self.conversation_client.create_session(
            draft=ConversationSessionDraft(
                title=command.message[:60],
                channel=command.channel,
                mission=_mission_payload(command),
                client_context=command.client_context,
            ),
            security_context=security_context,
        )


def _payload_hash(command: BobChatMessageCommand) -> str:
    encoded = json.dumps(
        asdict(command),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _mission_payload(command: BobChatMessageCommand) -> dict[str, Any] | None:
    if not command.mission:
        return None
    return {
        "id": command.mission.id,
        "prompt": command.mission.prompt,
        "context": command.mission.context or {},
    }


def _agent_id_payload(command: BobChatMessageCommand) -> str | None:
    if command.agent_id:
        return command.agent_id
    for key in ("agent_id", "bob_agent_id"):
        value = command.client_context.get(key)
        if value:
            return str(value)
    mission_context = command.mission.context if command.mission else None
    if isinstance(mission_context, dict):
        for key in ("agent_id", "bob_agent_id"):
            value = mission_context.get(key)
            if value:
                return str(value)
    return None


def _public_narration_steps(raw_steps: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_steps, list):
        return []
    public_steps: list[dict[str, Any]] = []
    for raw_step in raw_steps:
        if not isinstance(raw_step, Mapping):
            continue
        label = str(raw_step.get("label") or "").strip()
        if not label:
            continue
        safe_to_show = raw_step.get("safe_to_show")
        if safe_to_show is None:
            safe_to_show = raw_step.get("visible", True)
        public_steps.append(
            {
                "label": label,
                "kind": str(raw_step.get("kind") or _narration_kind(label)),
                "status": str(raw_step.get("status") or "complete"),
                "safe_to_show": bool(safe_to_show),
            }
        )
    return public_steps


def _narration_kind(label: str) -> str:
    if label.startswith("outil_"):
        return "lookup"
    if label in {"provider_runtime", "demande_recue"}:
        return "validate"
    if label == "reponse_complete":
        return "summarize"
    return "lookup"
