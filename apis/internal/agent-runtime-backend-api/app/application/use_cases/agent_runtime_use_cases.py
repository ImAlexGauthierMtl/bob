"""Agent Runtime application use cases."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Optional, Protocol
from uuid import uuid4

from app.application.ports import RuntimeProviderPort, RuntimeToolRegistryPort
from app.domain import (
    AgentConfirmation,
    AgentRun,
    AgentRuntimeError,
    AgentRuntimeNotFoundError,
    InternalContext,
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
        messages = _build_messages(prompt=prompt, channel=channel, metadata=metadata)
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


def _build_messages(*, prompt: str, channel: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    memory_context = metadata.get("memory_context") if isinstance(metadata, dict) else None
    memory_summary = _safe_memory_summary(memory_context if isinstance(memory_context, dict) else {})
    return [
        {
            "role": "system",
            "content": (
                "Tu es Bob dans Croo Digital Experience. Tu reponds clairement en francais. "
                "Tu peux utiliser uniquement les outils fournis au run. "
                "Tu ne reveles jamais de secret, tu verifies les donnees utiles et tu demandes une confirmation "
                "avant toute action d'ecriture ou action irreversible. "
                f"Canal actif: {channel}. Contexte memoire: {memory_summary}"
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]


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
