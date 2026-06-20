"""Agent Runtime application use cases."""

from __future__ import annotations

import json
import hashlib
import os
import re
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Optional, Protocol
from uuid import uuid4

from app.application.mcp_intent_router import infer_external_mcp_intent
from app.application.ports import RuntimeProviderPort, RuntimeToolRegistryPort
from app.application.runtime_catalog_defaults import default_runtime_settings
from app.domain import (
    AgentConfirmation,
    AgentRun,
    AgentRuntimeError,
    AgentRuntimeNotFoundError,
    InternalContext,
    RuntimeCatalogItem,
    RuntimeModelResult,
    RuntimeToolCall,
)


MAX_TOOL_ITERATIONS = 5
MAX_TOOL_CALLS_PER_ITERATION = 3
MAX_TOTAL_TOOL_CALLS = 12


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
        runtime_catalog = await self.resolve_runtime_catalog(context=context, metadata=metadata)
        run_metadata = {
            **metadata,
            "runtime_catalog": runtime_catalog,
        }
        tools = self.tool_registry.list_tools(prompt=prompt, context=context, metadata=run_metadata)
        messages = _build_messages(prompt=prompt, channel=channel, metadata=run_metadata, tools=tools)
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
        pre_routed_tool_call = _pre_routed_mcp_tool_call(prompt=prompt, tools=tools)
        if pre_routed_tool_call:
            final_result = RuntimeModelResult(
                content="",
                provider="runtime_router",
                model="bob-mcp-intent-router",
                mode="runtime_mcp_intent_router",
                tool_calls=[pre_routed_tool_call],
                raw_metadata={
                    "trace_id": context.trace_id,
                    "phase": "tool_selection",
                    "routing": "deterministic_mcp_intent",
                },
            )
            narration_steps.append(
                {
                    "label": "intent_router",
                    "status": "complete",
                    "visible": True,
                }
            )
            provider_iterations = 0
        else:
            final_result = await _complete_provider_safely(
                provider=self.runtime_provider,
                messages=messages,
                tools=tools,
                trace_id=context.trace_id,
            )
            provider_iterations = 1
        narration_steps[1]["status"] = "complete"
        tool_loop_limit_reached = False

        while final_result.tool_calls:
            if provider_iterations >= MAX_TOOL_ITERATIONS or len(tool_results) >= MAX_TOTAL_TOOL_CALLS:
                tool_loop_limit_reached = True
                narration_steps.append(
                    {
                        "label": "tool_loop_limit_reached",
                        "status": "degraded",
                        "visible": True,
                    }
                )
                break

            remaining_tool_budget = MAX_TOTAL_TOOL_CALLS - len(tool_results)
            tool_calls = final_result.tool_calls[: min(MAX_TOOL_CALLS_PER_ITERATION, remaining_tool_budget)]
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
                        for tool_call in tool_calls
                    ],
                }
            )
            for tool_call in tool_calls:
                tool_result = await self.tool_registry.execute(
                    call=tool_call,
                    context=context,
                    metadata=run_metadata,
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
            final_result = await _complete_provider_safely(
                provider=self.runtime_provider,
                messages=messages,
                tools=tools,
                trace_id=context.trace_id,
            )
            provider_iterations += 1

        assistant_content = final_result.content.strip()
        if not assistant_content and tool_loop_limit_reached:
            assistant_content = _tool_loop_limit_content(prompt=prompt, executed_tools=len(tool_results))
        if not assistant_content:
            assistant_content = _fallback_assistant_content(prompt, channel)
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
                **run_metadata,
                "channel": channel,
                "provider": final_result.provider,
                "model": final_result.model,
                "tool_calls": [
                    {"id": item["id"], "tool": item["tool"], "status": item["status"]}
                    for item in tool_results
                ],
                "tool_loop": {
                    "provider_iterations": provider_iterations,
                    "executed_tool_calls": len(tool_results),
                    "max_provider_iterations": MAX_TOOL_ITERATIONS,
                    "max_total_tool_calls": MAX_TOTAL_TOOL_CALLS,
                    "limit_reached": tool_loop_limit_reached,
                },
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

    async def resolve_runtime_catalog(
        self,
        *,
        context: InternalContext,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        settings = await self.get_runtime_settings(context=context)
        requested_agent_id = _requested_agent_id(metadata)
        agent = _find_catalog_entry(settings["agents"], requested_agent_id)
        selection_status = "requested"
        if agent is None:
            agent = _default_active_agent(settings["agents"])
            selection_status = "defaulted" if not requested_agent_id else "requested_not_found"

        skill_ids = _entry_ids(agent.get("skills") if isinstance(agent, dict) else [])
        tool_ids = _entry_ids(agent.get("tools") if isinstance(agent, dict) else [])
        skills = _entries_by_ids(settings["skills"], skill_ids)
        selected_tools = _entries_by_ids(settings["tools"], tool_ids)

        return {
            "requested_agent_id": requested_agent_id,
            "selection_status": selection_status,
            "agent": _public_catalog_entry(agent),
            "skills": [_public_catalog_entry(skill) for skill in skills],
            "tools": [_public_catalog_entry(tool) for tool in selected_tools],
        }

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
    agent_summary = _agent_runtime_summary(
        metadata.get("runtime_catalog") if isinstance(metadata, dict) else None
    )
    return [
        {
            "role": "system",
            "content": (
                "Tu es Bob dans Croo Digital Experience. Tu reponds clairement en francais. "
                "Tu peux utiliser uniquement les outils fournis au run. "
                "Quand la demande vise la memoire privee, la memoire organisation, un playbook support "
                "ou une famille MCP, utilise l'outil fourni plutot qu'une reponse estimee. "
                "Tu ne reveles jamais de secret, tu verifies les donnees utiles et tu demandes une confirmation "
                "avant toute action d'ecriture ou action irreversible. "
                f"Canal actif: {channel}. Contexte memoire: {memory_summary} "
                f"Catalogue agent: {agent_summary} "
                f"Runtime: {runtime_summary}"
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]


def _pre_routed_mcp_tool_call(*, prompt: str, tools: list[dict[str, Any]]) -> RuntimeToolCall | None:
    if not _tool_is_available(tools=tools, name="bob_mcp_gateway"):
        return None
    intent = infer_external_mcp_intent(prompt)
    if not intent:
        return None
    return RuntimeToolCall(
        id=f"intent_tool_{intent.family.replace('-', '_')}_{intent.capability.split('.')[-1].replace('-', '_')}",
        name="bob_mcp_gateway",
        arguments={
            "operation": "execute_capability",
            "family": intent.family,
            "capability": intent.capability,
            "query": prompt,
            "limit": intent.limit,
            "risk": intent.risk,
        },
    )


def _tool_is_available(*, tools: list[dict[str, Any]], name: str) -> bool:
    for tool in tools:
        function = tool.get("function") if isinstance(tool, dict) else None
        if isinstance(function, dict) and function.get("name") == name:
            return True
    return False


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


def _agent_runtime_summary(runtime_catalog: Any) -> str:
    if not isinstance(runtime_catalog, dict):
        return "agent non resolu."
    agent = runtime_catalog.get("agent") if isinstance(runtime_catalog.get("agent"), dict) else {}
    skills = runtime_catalog.get("skills") if isinstance(runtime_catalog.get("skills"), list) else []
    tools = runtime_catalog.get("tools") if isinstance(runtime_catalog.get("tools"), list) else []
    agent_name = _compact_text(str(agent.get("name") or "Bob"), 80)
    agent_id = _compact_text(str(agent.get("id") or "unknown"), 80)
    selection_status = _compact_text(str(runtime_catalog.get("selection_status") or "unknown"), 80)
    skill_details = _catalog_detail_lines(skills, fields=("description", "scope", "source"))
    tool_details = _catalog_detail_lines(tools, fields=("description", "family", "risk", "execution", "capability_id"))
    return (
        f"agent={agent_name} ({agent_id}), "
        f"selection={selection_status}, "
        f"skills={skill_details or 'aucun'}, tools={tool_details or 'aucun'}."
    )


def _catalog_detail_lines(entries: list[Any], *, fields: tuple[str, ...]) -> str:
    lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = _compact_text(str(entry.get("name") or entry.get("id") or ""), 80)
        if not name:
            continue
        details = [
            f"{field}={_compact_text(str(entry[field]), 160)}"
            for field in fields
            if entry.get(field)
        ]
        lines.append(f"{name} ({'; '.join(details)})" if details else name)
    return " | ".join(lines[:8])


def _compact_text(value: str, limit: int) -> str:
    compacted = " ".join(_redact_catalog_secrets(value).split())
    if len(compacted) <= limit:
        return compacted
    return f"{compacted[: max(0, limit - 3)]}..."


def _redact_catalog_secrets(value: str) -> str:
    redacted = re.sub(
        r"(?i)\b(api[_-]?key|token|secret|password|passwd)\s*[:=]\s*[^,\s;]+",
        lambda match: f"{match.group(1)}=[redacted]",
        value,
    )
    redacted = re.sub(
        r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+",
        "Bearer [redacted]",
        redacted,
    )
    return re.sub(r"\b(?:sk|fw)_[A-Za-z0-9_-]{8,}\b", "[redacted]", redacted)


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


def _tool_loop_limit_content(*, prompt: str, executed_tools: int) -> str:
    normalized_prompt = " ".join(prompt.split())[:180]
    return (
        "Bob a interrompu la boucle d'outils pour garder l'execution sous controle. "
        f"Outils executes: {executed_tools}. "
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


def _requested_agent_id(metadata: dict[str, Any]) -> str | None:
    for key in ("agent_id", "bob_agent_id"):
        value = metadata.get(key)
        if value:
            return str(value)
    client_context = metadata.get("client_context")
    if isinstance(client_context, dict):
        for key in ("agent_id", "bob_agent_id"):
            value = client_context.get(key)
            if value:
                return str(value)
    mission = metadata.get("mission")
    mission_context = mission.get("context") if isinstance(mission, dict) else None
    if isinstance(mission_context, dict):
        for key in ("agent_id", "bob_agent_id"):
            value = mission_context.get(key)
            if value:
                return str(value)
    return None


def _find_catalog_entry(entries: list[dict[str, Any]], entry_id: str | None) -> dict[str, Any] | None:
    if not entry_id:
        return None
    normalized = entry_id.strip().lower()
    for entry in entries:
        if str(entry.get("id") or "").lower() == normalized:
            return entry
        if str(entry.get("name") or "").lower() == normalized:
            return entry
    return None


def _default_active_agent(entries: list[dict[str, Any]]) -> dict[str, Any]:
    for entry in entries:
        if entry.get("status") == "active":
            return entry
    return entries[0] if entries else {"id": "agent-bob-orchestrator", "name": "Bob Orchestrator"}


def _entry_ids(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip() for item in value if str(item).strip()}


def _entries_by_ids(entries: list[dict[str, Any]], entry_ids: set[str]) -> list[dict[str, Any]]:
    if not entry_ids:
        return []
    lowered = {entry_id.lower() for entry_id in entry_ids}
    return [
        entry
        for entry in entries
        if str(entry.get("id") or "").lower() in lowered
        or str(entry.get("name") or "").lower() in lowered
    ]


def _public_catalog_entry(entry: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(entry, dict):
        return {}
    public_keys = {
        "id",
        "name",
        "description",
        "provider_id",
        "status",
        "skills",
        "tools",
        "scope",
        "family",
        "risk",
        "execution",
        "servers",
        "skill",
        "capabilities",
        "capability_id",
        "capability_file",
        "mcp_tools",
        "source",
    }
    return {key: value for key, value in entry.items() if key in public_keys}


async def _complete_provider_safely(
    *,
    provider: RuntimeProviderPort,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    trace_id: str,
) -> RuntimeModelResult:
    try:
        return await provider.complete(messages=messages, tools=tools, trace_id=trace_id)
    except Exception as exc:
        return RuntimeModelResult(
            content=(
                "Bob ne peut pas joindre le fournisseur LLM pour le moment. "
                "Le runtime a conserve la trace et les resultats d'outils deja disponibles."
            ),
            provider="runtime_provider",
            model="unknown",
            mode="provider_degraded",
            raw_metadata={
                "trace_id": trace_id,
                "provider_error": type(exc).__name__,
            },
        )


def _payload_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _request_payload_hash(*, collection: str, payload: dict[str, Any]) -> str:
    normalized = {
        "collection": collection,
        "payload": {key: value for key, value in payload.items() if value is not None},
    }
    return _payload_hash(normalized)
