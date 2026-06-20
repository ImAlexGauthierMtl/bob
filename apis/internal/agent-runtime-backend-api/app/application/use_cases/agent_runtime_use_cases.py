"""Agent Runtime application use cases."""

from __future__ import annotations

import json
import hashlib
import os
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Optional, Protocol
from uuid import uuid4

from app.application.ports import RuntimeProviderPort, RuntimeToolRegistryPort
from app.application.runtime_catalog_defaults import default_runtime_settings
from app.domain import (
    AgentConfirmation,
    AgentRun,
    AgentRuntimeError,
    AgentRuntimeNotFoundError,
    InternalContext,
    RuntimeCatalogItem,
)


class AgentRuntimeRepositoryPort(Protocol):
    def create_run(self, *, run: AgentRun) -> AgentRun:
        ...

    def get_run(
        self,
        *,
        run_id: str,
        tenant_id: str,
        user_id: str,
    ) -> Optional[AgentRun]:
        ...

    def get_run_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> Optional[AgentRun]:
        ...

    def update_run(self, *, run: AgentRun) -> AgentRun:
        ...

    def get_confirmation(
        self,
        *,
        confirmation_id: str,
        run_id: str,
        tenant_id: str,
        user_id: str,
    ) -> Optional[AgentConfirmation]:
        ...

    def update_confirmation(self, *, confirmation: AgentConfirmation) -> AgentConfirmation:
        ...

    def list_catalog_items(
        self,
        *,
        tenant_id: str,
        user_id: str,
        collection: str,
    ) -> list[RuntimeCatalogItem]:
        ...

    def get_catalog_item_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        collection: str,
        idempotency_key: str,
    ) -> Optional[RuntimeCatalogItem]:
        ...

    def create_catalog_item(self, *, item: RuntimeCatalogItem) -> RuntimeCatalogItem:
        ...


class AgentRuntimeUseCases:
    def __init__(
        self,
        *,
        repo: AgentRuntimeRepositoryPort,
        runtime_provider: RuntimeProviderPort,
        tool_registry: RuntimeToolRegistryPort,
    ) -> None:
        self.repo = repo
        self.runtime_provider = runtime_provider
        self.tool_registry = tool_registry

    async def create_run(
        self,
        *,
        context: InternalContext,
        session_id: str,
        input_message_id: str,
        prompt: str,
        channel: str,
        metadata: dict[str, Any],
        idempotency_key: str,
    ) -> AgentRun:
        existing = self.repo.get_run_by_idempotency_key(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            idempotency_key=idempotency_key,
        )
        if existing:
            return existing

        now = _utc_now()
        tools = self.tool_registry.list_tools(prompt=prompt, context=context, metadata=metadata)
        messages = _build_messages(prompt=prompt, channel=channel, metadata=metadata, tools=tools)
        tool_results: list[dict[str, Any]] = []
        narration_steps = [
            {
                "label": "demande_recue",
                "status": "complete",
                "visible": True,
            },
            {
                "label": "provider_runtime",
                "status": "running",
                "visible": True,
            },
        ]
        final_result = await self.runtime_provider.complete(
            messages=messages,
            tools=tools,
            trace_id=context.trace_id,
        )
        narration_steps[1]["status"] = "complete"

        if final_result.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": final_result.content or "",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.name,
                                "arguments": json.dumps(tool_call.arguments, ensure_ascii=False),
                            },
                        }
                        for tool_call in final_result.tool_calls
                    ],
                }
            )
            for tool_call in final_result.tool_calls[:3]:
                tool_result = await self.tool_registry.execute(
                    call=tool_call,
                    context=context,
                    metadata=metadata,
                )
                tool_results.append(
                    {
                        "id": tool_result.call_id,
                        "tool": tool_result.name,
                        "status": tool_result.status,
                        "content": tool_result.content,
                        "metadata": tool_result.metadata,
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_result.call_id,
                        "name": tool_result.name,
                        "content": tool_result.content,
                    }
                )
                narration_steps.append(
                    {
                        "label": f"outil_{tool_result.name}",
                        "status": tool_result.status,
                        "visible": True,
                    }
                )
            final_result = await self.runtime_provider.complete(
                messages=messages,
                tools=tools,
                trace_id=context.trace_id,
            )

        assistant_content = final_result.content.strip() or _fallback_assistant_content(prompt, channel)
        completed_at = _utc_now()
        run = AgentRun(
            id=f"run_{uuid4().hex}",
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            session_id=session_id,
            input_message_id=input_message_id,
            status="completed",
            mode=final_result.mode,
            trace_id=context.trace_id,
            assistant_content=assistant_content,
            created_at=now,
            completed_at=completed_at,
            idempotency_key=idempotency_key,
            metadata={
                **metadata,
                "channel": channel,
                "provider": final_result.provider,
                "model": final_result.model,
                "tool_calls": [
                    {"id": item["id"], "tool": item["tool"], "status": item["status"]}
                    for item in tool_results
                ],
                "runtime": final_result.raw_metadata,
            },
            narration_steps=[
                *narration_steps,
                {
                    "label": "reponse_complete",
                    "status": "complete",
                    "visible": True,
                },
            ],
            actions=tool_results,
            artifacts=[],
        )
        return self.repo.create_run(run=run)

    async def get_run(self, *, context: InternalContext, run_id: str) -> AgentRun:
        run = self.repo.get_run(
            run_id=run_id,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
        )
        if not run:
            raise AgentRuntimeNotFoundError("run_not_found")
        return run

    async def cancel_run(self, *, context: InternalContext, run_id: str) -> AgentRun:
        run = await self.get_run(context=context, run_id=run_id)
        if run.status in {"completed", "cancelled", "failed"}:
            raise AgentRuntimeError("run_not_cancelable")
        return self.repo.update_run(
            run=replace(
                run,
                status="cancelled",
                cancelled_at=_utc_now(),
            )
        )

    async def resolve_confirmation(
        self,
        *,
        context: InternalContext,
        run_id: str,
        confirmation_id: str,
        decision: str,
    ) -> AgentConfirmation:
        confirmation = self.repo.get_confirmation(
            confirmation_id=confirmation_id,
            run_id=run_id,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
        )
        if not confirmation:
            raise AgentRuntimeNotFoundError("confirmation_not_found")
        if confirmation.status != "pending":
            raise AgentRuntimeError("confirmation_already_resolved")
        return self.repo.update_confirmation(
            confirmation=replace(
                confirmation,
                status=decision,
                resolved_at=_utc_now(),
            )
        )

    async def get_runtime_settings(self, *, context: InternalContext) -> dict[str, Any]:
        settings = default_runtime_settings(
            active_provider=os.environ.get("AGENT_RUNTIME_PROVIDER", "auto"),
        )
        for collection in ("agents", "skills", "tools"):
            custom_items = self.repo.list_catalog_items(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                collection=collection,
            )
            settings[collection].extend(item.payload for item in custom_items)
        return settings

    async def create_runtime_catalog_item(
        self,
        *,
        context: InternalContext,
        collection: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        if collection not in {"agents", "skills", "tools"}:
            raise AgentRuntimeError("runtime_collection_invalid")
        payload_hash = _request_payload_hash(collection=collection, payload=payload)
        item_payload = _catalog_payload(collection=collection, payload=payload)
        existing = self.repo.get_catalog_item_by_idempotency_key(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            collection=collection,
            idempotency_key=idempotency_key,
        )
        if existing:
            if existing.payload_hash != payload_hash:
                raise AgentRuntimeError("idempotency_conflict")
            return {
                "item": existing.payload,
                "runtime": await self.get_runtime_settings(context=context),
            }

        item = RuntimeCatalogItem(
            id=item_payload["id"],
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            collection=collection,
            name=item_payload["name"],
            payload=item_payload,
            payload_hash=payload_hash,
            idempotency_key=idempotency_key,
            created_at=_utc_now(),
        )
        created = self.repo.create_catalog_item(item=item)
        return {
            "item": created.payload,
            "runtime": await self.get_runtime_settings(context=context),
        }


def _build_messages(
    *,
    prompt: str,
    channel: str,
    metadata: dict[str, Any],
    tools: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    memory_context = metadata.get("memory_context") if isinstance(metadata, dict) else None
    memory_summary = _safe_memory_summary(memory_context if isinstance(memory_context, dict) else {})
    runtime_summary = _runtime_summary(tools)
    return [
        {
            "role": "system",
            "content": (
                "Tu es Bob dans Croo Digital Experience. Tu reponds clairement en francais. "
                "Tu peux utiliser uniquement les outils fournis au run. "
                "Tu ne reveles jamais de secret, tu verifies les donnees utiles et tu demandes une confirmation "
                "avant toute action d'ecriture ou action irreversible. "
                f"Canal actif: {channel}. Contexte memoire: {memory_summary} "
                f"Runtime: {runtime_summary}"
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]


def _runtime_summary(tools: list[dict[str, Any]]) -> str:
    provider_mode = os.environ.get("AGENT_RUNTIME_PROVIDER", "auto").strip().lower() or "auto"
    fireworks_model = os.environ.get("FIREWORKS_MODEL", "accounts/fireworks/models/kimi-k2p7-code")
    provider = "fireworks" if provider_mode in {"auto", "fireworks"} and os.environ.get("FIREWORKS_API_KEY") else "local"
    tool_names = []
    for tool in tools[:8]:
        function = tool.get("function") if isinstance(tool, dict) else None
        if isinstance(function, dict) and function.get("name"):
            tool_names.append(str(function["name"]))
    tools_summary = ", ".join(tool_names) if tool_names else "aucun outil fourni"
    return (
        f"provider={provider}, mode={provider_mode}, "
        f"modele_fireworks={fireworks_model}, outils={tools_summary}."
    )


def _safe_memory_summary(memory_context: dict[str, Any]) -> str:
    private_count = len(memory_context.get("private") or [])
    organization_count = len(memory_context.get("organization") or [])
    degraded = ", ".join(str(item) for item in (memory_context.get("degraded") or [])[:3])
    return (
        f"{private_count} memoires privees, {organization_count} memoires organisation. "
        f"Degradations: {degraded or 'aucune'}."
    )


def _fallback_assistant_content(prompt: str, channel: str) -> str:
    normalized_prompt = " ".join(prompt.split())[:180]
    return (
        "Bob a traite la demande dans le runtime agentique CDE. "
        f"Canal: {channel}. "
        f"Demande: {normalized_prompt}"
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _catalog_payload(*, collection: str, payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise AgentRuntimeError("name_required")
    item_id = str(payload.get("id") or f"{collection[:-1]}-{uuid4().hex[:10]}")
    defaults: dict[str, Any]
    if collection == "agents":
        defaults = {
            "description": "",
            "provider_id": "fireworks-kimi",
            "status": "draft",
            "skills": [],
            "tools": [],
        }
    elif collection == "skills":
        defaults = {
            "description": "",
            "status": "draft",
            "scope": "shared_clean",
        }
    else:
        defaults = {
            "description": "",
            "family": "custom",
            "risk": "read",
            "status": "draft",
            "execution": "mcp_gateway_pending",
        }
    return {
        "id": item_id,
        "name": name,
        **defaults,
        **{key: value for key, value in payload.items() if value is not None},
        "id": item_id,
        "name": name,
    }


def _payload_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _request_payload_hash(*, collection: str, payload: dict[str, Any]) -> str:
    normalized = {
        "collection": collection,
        "payload": {key: value for key, value in payload.items() if value is not None},
    }
    return _payload_hash(normalized)
