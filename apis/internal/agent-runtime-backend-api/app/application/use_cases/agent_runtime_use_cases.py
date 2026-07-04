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
from app.application.runtime_catalog_defaults import default_runtime_settings, mcp_capabilities_for_family
from app.domain import (
    AgentConfirmation,
    AgentConfirmationResolution,
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

    def create_run_with_confirmations(
        self,
        *,
        run: AgentRun,
        confirmations: list[AgentConfirmation],
    ) -> AgentRun:
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

    def list_user_catalog_items(
        self,
        *,
        tenant_id: str,
        user_id: str,
        collection: str,
    ) -> list[RuntimeCatalogItem]:
        ...

    def get_catalog_item(
        self,
        *,
        item_id: str,
        tenant_id: str,
        collection: str,
        user_id: str | None = None,
    ) -> Optional[RuntimeCatalogItem]:
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

    def upsert_catalog_item(self, *, item: RuntimeCatalogItem) -> RuntimeCatalogItem:
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
        run_id = f"run_{uuid4().hex}"
        runtime_catalog = await self.resolve_runtime_catalog(context=context, metadata=metadata)
        tool_governance = await self.get_user_tool_access(context=context)
        runtime_catalog = _apply_tool_governance_to_runtime_catalog(
            runtime_catalog=runtime_catalog,
            tool_governance=tool_governance,
        )
        run_metadata = {
            **metadata,
            "source_prompt": prompt,
            "runtime_catalog": runtime_catalog,
            "tool_governance": tool_governance,
        }
        tools = self.tool_registry.list_tools(prompt=prompt, context=context, metadata=run_metadata)
        messages = _build_messages(prompt=prompt, channel=channel, metadata=run_metadata, tools=tools)
        tool_results: list[dict[str, Any]] = []
        show_tool_trace = _show_tool_trace(run_metadata)
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
        routing_events: list[dict[str, Any]] = []
        provider_supports_tool_choice = _provider_supports_tool_choice(self.runtime_provider)
        pre_routed_tool_call = (
            None
            if provider_supports_tool_choice
            else _pre_routed_mcp_tool_call(prompt=prompt, tools=tools)
        )
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
            routing_events.append(
                {
                    "router": "mcp_intent",
                    "strategy": "before_provider",
                    "tool": pre_routed_tool_call.name,
                }
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
            if provider_supports_tool_choice and not final_result.tool_calls:
                fallback_tool_call = _pre_routed_mcp_tool_call(prompt=prompt, tools=tools)
                if fallback_tool_call:
                    final_result = RuntimeModelResult(
                        content="",
                        provider="runtime_router",
                        model="bob-mcp-intent-router",
                        mode="runtime_mcp_intent_router_fallback",
                        tool_calls=[fallback_tool_call],
                        raw_metadata={
                            "trace_id": context.trace_id,
                            "phase": "tool_selection",
                            "routing": "deterministic_mcp_intent_after_provider",
                            "provider_first_mode": final_result.mode,
                            "provider_first_model": final_result.model,
                        },
                    )
                    narration_steps.append(
                        {
                            "label": "intent_router",
                            "status": "complete",
                            "visible": show_tool_trace,
                        }
                    )
                    routing_events.append(
                        {
                            "router": "mcp_intent",
                            "strategy": "after_provider_no_tool_call",
                            "tool": fallback_tool_call.name,
                            "provider_first_mode": final_result.raw_metadata.get("provider_first_mode"),
                            "provider_first_model": final_result.raw_metadata.get("provider_first_model"),
                        }
                    )
        narration_steps[1]["status"] = "complete"
        tool_loop_limit_reached = False
        pending_confirmations: list[AgentConfirmation] = []

        while final_result.tool_calls:
            if provider_iterations >= MAX_TOOL_ITERATIONS or len(tool_results) >= MAX_TOTAL_TOOL_CALLS:
                tool_loop_limit_reached = True
                narration_steps.append(
                    {
                        "label": "tool_loop_limit_reached",
                        "status": "degraded",
                        "visible": show_tool_trace,
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
                action_metadata = dict(tool_result.metadata)
                if tool_result.status == "requires_confirmation":
                    confirmation = AgentConfirmation(
                        id=f"confirm_{uuid4().hex}",
                        run_id=run_id,
                        tenant_id=context.tenant_id,
                        user_id=context.user_id,
                        status="pending",
                        label=_confirmation_label(
                            tool=tool_result.name,
                            content=tool_result.content,
                            metadata=action_metadata,
                        ),
                        created_at=_utc_now(),
                    )
                    pending_confirmations.append(confirmation)
                    action_metadata["confirmation_id"] = confirmation.id
                tool_results.append(
                    {
                        "id": tool_result.call_id,
                        "tool": tool_result.name,
                        "status": tool_result.status,
                        "content": tool_result.content,
                        "metadata": action_metadata,
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
                        "visible": show_tool_trace,
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
        if _has_pending_confirmation(tool_results):
            assistant_content = _pending_confirmation_content(channel=channel)
        completed_at = _utc_now()
        run = AgentRun(
            id=run_id,
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
                "routing": routing_events,
                "pending_confirmations": [
                    {
                        "id": confirmation.id,
                        "status": confirmation.status,
                        "label": confirmation.label,
                    }
                    for confirmation in pending_confirmations
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
        return self.repo.create_run_with_confirmations(
            run=run,
            confirmations=pending_confirmations,
        )

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
    ) -> AgentConfirmationResolution:
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
        updated_run: AgentRun | None = None
        execution_action: dict[str, Any] | None = None
        if decision == "confirmed":
            run = await self.get_run(context=context, run_id=run_id)
            source_action = _confirmation_source_action(run=run, confirmation_id=confirmation_id)
            if source_action:
                execution_result = await self.tool_registry.execute(
                    call=_confirmed_tool_call(source_action=source_action, confirmation_id=confirmation_id),
                    context=context,
                    metadata=run.metadata,
                )
                execution_action = {
                    "id": execution_result.call_id,
                    "tool": execution_result.name,
                    "status": execution_result.status,
                    "content": execution_result.content,
                    "metadata": {
                        **execution_result.metadata,
                        "confirmation_id": confirmation_id,
                        "confirmed_from_action_id": source_action.get("id"),
                    },
                }
                updated_run = self.repo.update_run(
                    run=replace(
                        run,
                        metadata=_metadata_with_resolved_confirmation(
                            metadata=run.metadata,
                            confirmation_id=confirmation_id,
                            decision=decision,
                            execution=execution_action,
                        ),
                        narration_steps=[
                            *run.narration_steps,
                            {
                                "label": "action_confirmee",
                                "status": execution_result.status,
                                "visible": True,
                            },
                        ],
                        actions=[*run.actions, execution_action],
                    )
                )
        updated_confirmation = self.repo.update_confirmation(
            confirmation=replace(
                confirmation,
                status=decision,
                resolved_at=_utc_now(),
            )
        )
        return AgentConfirmationResolution(
            confirmation=updated_confirmation,
            execution=execution_action,
            run=updated_run,
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

    async def get_tool_governance(self, *, context: InternalContext) -> dict[str, Any]:
        settings = await self.get_runtime_settings(context=context)
        defaults = {policy["id"]: policy for policy in _default_tool_policies(settings)}
        custom_items = self.repo.list_catalog_items(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            collection="tool_policies",
        )

        policies = dict(defaults)
        for item in custom_items:
            policy = _normalise_tool_policy(item.payload)
            policies[policy["id"]] = {
                **policies.get(policy["id"], {}),
                **policy,
                "source": "admin_policy",
            }

        sorted_policies = sorted(
            policies.values(),
            key=lambda item: (
                str(item.get("provider") or ""),
                str(item.get("family") or ""),
                str(item.get("display_name") or item.get("id") or ""),
            ),
        )
        return {
            "source": "agent-runtime-backend-api",
            "scope": "tenant",
            "tenant_id": context.tenant_id,
            "items": sorted_policies,
            "total": len(sorted_policies),
            "enabled_total": sum(1 for item in sorted_policies if item.get("enabled") is True),
            "collections": {
                "policies": "tool_policies",
                "user_preferences": "user_tool_preferences",
            },
        }

    async def update_tool_governance_policy(
        self,
        *,
        context: InternalContext,
        policy_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        policy = _tool_policy_payload(policy_id=policy_id, payload=payload)
        item = RuntimeCatalogItem(
            id=_catalog_storage_id("tool-policy", policy_id),
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            collection="tool_policies",
            name=policy["display_name"],
            payload=policy,
            payload_hash=_request_payload_hash(collection="tool_policies", payload=policy),
            idempotency_key=None,
            created_at=_utc_now(),
        )
        created = self.repo.upsert_catalog_item(item=item)
        return _normalise_tool_policy(created.payload)

    async def get_user_tool_access(self, *, context: InternalContext) -> dict[str, Any]:
        governance = await self.get_tool_governance(context=context)
        preferences = await self.get_user_tool_preferences(context=context)
        allowed = [item for item in governance["items"] if item.get("enabled") is True]
        return {
            "source": "agent-runtime-backend-api",
            "scope": "user",
            "tenant_id": context.tenant_id,
            "user_id": context.user_id,
            "preferences": preferences,
            "policies": governance["items"],
            "allowed_tools": allowed,
            "allowed_total": len(allowed),
        }

    async def get_user_tool_preferences(self, *, context: InternalContext) -> dict[str, Any]:
        item = self.repo.get_catalog_item(
            item_id=_catalog_storage_id("user-tool-preferences", context.user_id),
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            collection="user_tool_preferences",
        )
        if not item:
            return _default_user_tool_preferences()
        return _normalise_user_tool_preferences(item.payload)

    async def update_user_tool_preferences(
        self,
        *,
        context: InternalContext,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        preferences = _user_tool_preferences_payload(payload)
        item = RuntimeCatalogItem(
            id=_catalog_storage_id("user-tool-preferences", context.user_id),
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            collection="user_tool_preferences",
            name="User Tool Preferences",
            payload=preferences,
            payload_hash=_request_payload_hash(collection="user_tool_preferences", payload=preferences),
            idempotency_key=None,
            created_at=_utc_now(),
        )
        created = self.repo.upsert_catalog_item(item=item)
        return _normalise_user_tool_preferences(created.payload)


def _default_tool_policies(settings: dict[str, Any]) -> list[dict[str, Any]]:
    policies: list[dict[str, Any]] = []
    for tool in settings.get("tools", []):
        if not isinstance(tool, dict):
            continue
        tool_id = _runtime_tool_policy_id(tool)
        if not tool_id:
            continue
        policies.append(
            _normalise_tool_policy(
                {
                    "id": tool_id,
                    "display_name": str(tool.get("description") or tool.get("name") or tool_id),
                    "provider": _provider_for_runtime_tool(tool),
                    "integration_key": tool.get("family"),
                    "tool_key": tool.get("name") or tool.get("id"),
                    "family": tool.get("family"),
                    "capability": tool.get("capability_id") or tool.get("name"),
                    "risk": tool.get("risk") or "read",
                    "enabled": _runtime_tool_enabled_by_default(tool),
                    "team_scope": [],
                    "sync_enabled": False,
                    "sync_mode": "none",
                    "data_mapping": {},
                    "notes": tool.get("source") or tool.get("execution"),
                    "source": "runtime_default",
                }
            )
        )

    for capability in settings.get("mcp", {}).get("capabilities", []):
        if not isinstance(capability, dict):
            continue
        policy_id = str(capability.get("qualified_id") or "").strip()
        if not policy_id:
            continue
        policies.append(
            _normalise_tool_policy(
                {
                    "id": policy_id,
                    "display_name": capability.get("title") or policy_id,
                    "provider": "mcp",
                    "integration_key": capability.get("family"),
                    "tool_key": ",".join(str(item) for item in capability.get("tools", []) if item),
                    "family": capability.get("family"),
                    "capability": capability.get("id"),
                    "risk": capability.get("risk") or "read",
                    "enabled": _capability_enabled_by_default(capability),
                    "team_scope": [],
                    "sync_enabled": False,
                    "sync_mode": "none",
                    "data_mapping": _capability_data_mapping(capability),
                    "notes": capability.get("file"),
                    "source": "mcp_catalog",
                }
            )
        )
    return _dedupe_policies(policies)


def _runtime_tool_policy_id(tool: dict[str, Any]) -> str:
    family = _clean_string(tool.get("family"))
    capability = _clean_string(tool.get("capability_id"))
    if family and capability and capability != family:
        return capability if "." in capability else f"{family}.{capability}"
    return str(tool.get("id") or tool.get("name") or "").strip()


def _runtime_tool_enabled_by_default(tool: dict[str, Any]) -> bool:
    risk = _clean_string(tool.get("risk")) or "read"
    if risk == "destructive-confirmed":
        return False
    status = _clean_string(tool.get("status"))
    if not status:
        return True
    return status.lower() not in {"disabled", "inactive", "archived", "deleted"}


def _capability_data_mapping(capability: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "capability_path": capability.get("capability_path"),
        "runtime_status": capability.get("runtime_status"),
        "connector_status": capability.get("connector_status"),
    }
    for key in (
        "api_surface",
        "api_base_hint",
        "portal_url",
        "endpoint",
        "http_method",
        "api_object",
        "api_action",
        "doc_section",
        "doc_operation",
        "doc_url",
        "api_scope",
        "read_only_test",
        "guardrail",
    ):
        value = capability.get(key)
        if value not in (None, ""):
            mapping[key] = value
    return mapping


def _provider_for_runtime_tool(tool: dict[str, Any]) -> str:
    execution = str(tool.get("execution") or "")
    if "mcp" in execution:
        return "mcp"
    if str(tool.get("family") or "") in {"mail-calendar", "slack", "teams"}:
        return "pipedream"
    return "internal"


def _capability_enabled_by_default(capability: dict[str, Any]) -> bool:
    status = str(capability.get("runtime_status") or "")
    risk = str(capability.get("risk") or "read")
    if risk == "destructive-confirmed":
        return False
    return status in {
        "local_runtime_active",
        "local_adapter_active",
        "remote_adapter_configured",
        "confirmation_gated_contract",
    }


def _dedupe_policies(policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for policy in policies:
        policy_id = str(policy["id"])
        existing = by_id.get(policy_id)
        if existing:
            by_id[policy_id] = {
                **existing,
                **policy,
                "enabled": bool(existing.get("enabled")) or bool(policy.get("enabled")),
            }
            continue
        by_id[policy_id] = policy
    return list(by_id.values())


def _tool_policy_payload(*, policy_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    merged = {"id": policy_id, **payload}
    return _normalise_tool_policy(merged)


def _normalise_tool_policy(payload: dict[str, Any]) -> dict[str, Any]:
    policy_id = _required_clean_string(payload.get("id"), "tool_policy_id")
    display_name = _clean_string(payload.get("display_name")) or _clean_string(payload.get("name")) or policy_id
    sync_mode = _clean_string(payload.get("sync_mode")) or "none"
    if sync_mode not in {"none", "read_only", "import", "two_way"}:
        raise AgentRuntimeError("tool_policy_sync_mode_invalid")
    return {
        "id": policy_id,
        "display_name": display_name[:180],
        "provider": _clean_string(payload.get("provider")) or "mcp",
        "integration_key": _clean_string(payload.get("integration_key")),
        "tool_key": _clean_string(payload.get("tool_key")),
        "family": _clean_string(payload.get("family")),
        "capability": _clean_string(payload.get("capability")),
        "risk": _clean_string(payload.get("risk")) or "read",
        "enabled": bool(payload.get("enabled", True)),
        "team_scope": _clean_string_list(payload.get("team_scope")),
        "sync_enabled": bool(payload.get("sync_enabled", False)),
        "sync_mode": sync_mode,
        "data_mapping": payload.get("data_mapping") if isinstance(payload.get("data_mapping"), dict) else {},
        "notes": _clean_string(payload.get("notes")),
        "source": _clean_string(payload.get("source")) or "admin_policy",
    }


def _default_user_tool_preferences() -> dict[str, Any]:
    return {
        "preferred_email_provider": "auto",
        "preferred_calendar_provider": "auto",
        "require_write_confirmation": True,
        "show_tool_trace": True,
        "allow_personal_connectors": True,
    }


def _user_tool_preferences_payload(payload: dict[str, Any]) -> dict[str, Any]:
    defaults = _default_user_tool_preferences()
    preferences = {
        **defaults,
        **{
            key: value
            for key, value in payload.items()
            if key in defaults
        },
    }
    return _normalise_user_tool_preferences(preferences)


def _normalise_user_tool_preferences(payload: dict[str, Any]) -> dict[str, Any]:
    email_provider = _preference_choice(
        payload.get("preferred_email_provider"),
        allowed={"auto", "gmail", "microsoft_outlook", "ask"},
        default="auto",
    )
    calendar_provider = _preference_choice(
        payload.get("preferred_calendar_provider"),
        allowed={"auto", "google_calendar", "microsoft_outlook", "ask"},
        default="auto",
    )
    return {
        "preferred_email_provider": email_provider,
        "preferred_calendar_provider": calendar_provider,
        "require_write_confirmation": bool(payload.get("require_write_confirmation", True)),
        "show_tool_trace": bool(payload.get("show_tool_trace", True)),
        "allow_personal_connectors": bool(payload.get("allow_personal_connectors", True)),
    }


def _metadata_tool_preferences(metadata: dict[str, Any]) -> dict[str, Any]:
    governance = metadata.get("tool_governance") if isinstance(metadata, dict) else None
    preferences = governance.get("preferences") if isinstance(governance, dict) else None
    if not isinstance(preferences, dict):
        return _default_user_tool_preferences()
    return _normalise_user_tool_preferences(preferences)


def _show_tool_trace(metadata: dict[str, Any]) -> bool:
    return bool(_metadata_tool_preferences(metadata).get("show_tool_trace", True))


def _tool_preference_summary(metadata: dict[str, Any]) -> str:
    preferences = _metadata_tool_preferences(metadata)
    return (
        f"email={preferences['preferred_email_provider']}, "
        f"calendrier={preferences['preferred_calendar_provider']}, "
        f"confirmation_ecriture={preferences['require_write_confirmation']}, "
        f"trace_outils={preferences['show_tool_trace']}, "
        f"connecteurs_personnels={preferences['allow_personal_connectors']}."
    )


def _preference_choice(value: Any, *, allowed: set[str], default: str) -> str:
    candidate = str(value or "").strip()
    return candidate if candidate in allowed else default


def _catalog_storage_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
    return f"{prefix}-{digest}"[:64]


def _required_clean_string(value: Any, code: str) -> str:
    cleaned = _clean_string(value)
    if not cleaned:
        raise AgentRuntimeError(code)
    return cleaned


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


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
    mcp_tool_selection = _mcp_tool_selection_summary(tools)
    agent_summary = _agent_runtime_summary(
        metadata.get("runtime_catalog") if isinstance(metadata, dict) else None
    )
    preference_summary = _tool_preference_summary(metadata)
    return [
        {
            "role": "system",
            "content": (
                "Tu es Bob dans Croo Digital Experience. Tu reponds clairement en francais. "
                "Tu peux utiliser uniquement les outils fournis au run. "
                "Quand la demande vise la memoire privee, la memoire organisation, un playbook support "
                "ou une famille MCP, utilise l'outil fourni plutot qu'une reponse estimee. "
                "Si bob_mcp_gateway est disponible et que la demande vise une famille MCP, emets "
                "un tool_call bob_mcp_gateway au premier tour avec operation=execute_capability, "
                "family, capability et risk alignes au catalogue. "
                "N'appelle bob_runtime_status que pour une demande de statut, diagnostic ou etat runtime. "
                "Tu ne reveles jamais de secret, tu verifies les donnees utiles et tu respectes la politique "
                "de confirmation du runtime avant toute ecriture; les actions irreversibles restent toujours gatees. "
                f"Canal actif: {channel}. Contexte memoire: {memory_summary} "
                f"Catalogue agent: {agent_summary} "
                f"Preferences outils: {preference_summary} "
                f"Selection MCP: {mcp_tool_selection} "
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


def _provider_supports_tool_choice(provider: RuntimeProviderPort) -> bool:
    return bool(getattr(provider, "supports_tool_choice", False))


def _tool_is_available(*, tools: list[dict[str, Any]], name: str) -> bool:
    for tool in tools:
        function = tool.get("function") if isinstance(tool, dict) else None
        if isinstance(function, dict) and function.get("name") == name:
            return True
    return False


def _confirmation_label(*, tool: str, content: str, metadata: dict[str, Any]) -> str:
    parsed: dict[str, Any] = {}
    try:
        raw = json.loads(content)
        if isinstance(raw, dict):
            parsed = raw
    except json.JSONDecodeError:
        parsed = {}
    family = str(metadata.get("family") or parsed.get("family") or "tool")
    capability = str(parsed.get("capability") or metadata.get("capability") or "")
    risk = str(metadata.get("risk") or parsed.get("risk") or "write")
    label_parts = [tool, family]
    if capability:
        label_parts.append(capability)
    label_parts.append(risk)
    return _compact_text(" / ".join(label_parts), 160)


def _confirmation_source_action(*, run: AgentRun, confirmation_id: str) -> dict[str, Any] | None:
    for action in run.actions:
        metadata = action.get("metadata") if isinstance(action, dict) else None
        if isinstance(metadata, dict) and metadata.get("confirmation_id") == confirmation_id:
            return action
    return None


def _confirmed_tool_call(*, source_action: dict[str, Any], confirmation_id: str) -> RuntimeToolCall:
    content = _parse_json_object(source_action.get("content"))
    metadata = source_action.get("metadata") if isinstance(source_action.get("metadata"), dict) else {}
    family = str(metadata.get("family") or content.get("family") or "")
    capability = str(metadata.get("capability") or content.get("capability") or "")
    request = content.get("request") if isinstance(content.get("request"), dict) else {}
    arguments: dict[str, Any] = {
        "operation": str(metadata.get("operation") or content.get("operation") or "execute_capability"),
        "family": family,
        "capability": capability,
        "risk": str(metadata.get("risk") or content.get("risk") or "write"),
        "query": content.get("query") or request.get("query") or "",
        "confirmed": True,
        "confirmation_id": confirmation_id,
    }
    for key in ("limit", "offset", "project_id", "request_id", "status"):
        if key in request:
            arguments[key] = request[key]
    return RuntimeToolCall(
        id=f"confirmed_{confirmation_id}",
        name=str(source_action.get("tool") or "bob_mcp_gateway"),
        arguments={key: value for key, value in arguments.items() if value not in {None, ""}},
    )


def _metadata_with_resolved_confirmation(
    *,
    metadata: dict[str, Any],
    confirmation_id: str,
    decision: str,
    execution: dict[str, Any] | None,
) -> dict[str, Any]:
    pending = metadata.get("pending_confirmations") if isinstance(metadata, dict) else None
    resolved_pending = []
    for item in pending if isinstance(pending, list) else []:
        if isinstance(item, dict) and item.get("id") == confirmation_id:
            resolved_pending.append({**item, "status": decision})
        elif isinstance(item, dict):
            resolved_pending.append(item)
    executions = metadata.get("confirmed_executions") if isinstance(metadata, dict) else None
    return {
        **metadata,
        "pending_confirmations": resolved_pending,
        "confirmed_executions": [
            *(executions if isinstance(executions, list) else []),
            *([execution] if execution else []),
        ],
    }


def _parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _has_pending_confirmation(tool_results: list[dict[str, Any]]) -> bool:
    return any(item.get("status") == "requires_confirmation" for item in tool_results if isinstance(item, dict))


def _pending_confirmation_content(*, channel: str) -> str:
    if channel == "voice_phone":
        return (
            "J'ai préparé l'action demandée. Elle attend ta confirmation avant toute écriture externe. "
            "Aucun message, connecteur ou outil externe n'a été exécuté pour l'instant."
        )
    return (
        "J'ai préparé l'action demandée. Elle nécessite ta confirmation avant toute écriture externe. "
        "Aucun message, connecteur ou outil externe n'a été exécuté pour l'instant. "
        "Après confirmation, Bob affichera le statut réel de l'exécution ou du connecteur."
    )


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


def _mcp_tool_selection_summary(tools: list[dict[str, Any]]) -> str:
    if not _tool_is_available(tools=tools, name="bob_mcp_gateway"):
        return "bob_mcp_gateway non expose."
    examples = [
        _capability_hint("slack", "draft-send"),
        _capability_hint("slack", "messages-read-search"),
        _capability_hint("teams", "draft-send"),
        _capability_hint("mail-calendar", "mail-draft-send"),
        _capability_hint("factory", "requests-queues"),
        _capability_hint("gitlab-code", "files"),
        _capability_hint("workspace-files", "local-files"),
        _capability_hint("support-memory", "search"),
    ]
    guide = " | ".join(item for item in examples if item)
    return (
        "utilise operation=execute_capability; risk accepte read, draft, "
        "write-requested, destructive-confirmed; exemples: "
        f"{guide or 'catalogue indisponible'}."
    )


def _capability_hint(family: str, capability_id: str) -> str:
    for item in mcp_capabilities_for_family(family):
        if item.get("id") == capability_id:
            return f"{family}.{capability_id}->risk={item.get('risk')}"
    return ""


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


def _apply_tool_governance_to_runtime_catalog(
    *,
    runtime_catalog: dict[str, Any],
    tool_governance: dict[str, Any],
) -> dict[str, Any]:
    selected_tools = runtime_catalog.get("tools") if isinstance(runtime_catalog, dict) else None
    policies = tool_governance.get("policies") if isinstance(tool_governance, dict) else None
    allowed_tools = tool_governance.get("allowed_tools") if isinstance(tool_governance, dict) else None
    if not isinstance(selected_tools, list) or not isinstance(policies, list) or not isinstance(allowed_tools, list):
        return runtime_catalog

    filtered_tools = [
        tool
        for tool in selected_tools
        if isinstance(tool, dict) and _runtime_tool_allowed_by_governance(tool, policies, allowed_tools)
    ]
    return {
        **runtime_catalog,
        "tools": filtered_tools,
        "governance": {
            "source": tool_governance.get("source"),
            "allowed_total": tool_governance.get("allowed_total"),
            "filtered_tool_count": len(selected_tools) - len(filtered_tools),
        },
    }


def _runtime_tool_allowed_by_governance(
    tool: dict[str, Any],
    policies: list[Any],
    allowed_tools: list[Any],
) -> bool:
    tool_keys = {
        _compact_governance_key(tool.get("id")),
        _compact_governance_key(tool.get("name")),
        _compact_governance_key(tool.get("tool_key")),
        _compact_governance_key(tool.get("capability_id")),
    }
    tool_keys.discard("")
    if not tool_keys:
        return True

    matching_policy_exists = False
    for policy in policies:
        if not isinstance(policy, dict):
            continue
        policy_keys = _runtime_policy_governance_keys(policy)
        if tool_keys & policy_keys:
            matching_policy_exists = True
            break
    if not matching_policy_exists:
        return True

    for policy in allowed_tools:
        if not isinstance(policy, dict):
            continue
        policy_keys = _runtime_policy_governance_keys(policy)
        if tool_keys & policy_keys:
            return True
    return False


def _runtime_policy_governance_keys(policy: dict[str, Any]) -> set[str]:
    policy_keys = {
        _compact_governance_key(policy.get("id")),
        _compact_governance_key(policy.get("tool_key")),
        _compact_governance_key(policy.get("capability")),
    }
    policy_keys.discard("")
    return policy_keys


def _compact_governance_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-")


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
