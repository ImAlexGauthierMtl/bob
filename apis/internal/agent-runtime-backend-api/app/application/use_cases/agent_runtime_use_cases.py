"""Agent Runtime application use cases."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Optional, Protocol
from uuid import uuid4

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
    def __init__(self, *, repo: AgentRuntimeRepositoryPort) -> None:
        self.repo = repo

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
        run = AgentRun(
            id=f"run_{uuid4().hex}",
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            session_id=session_id,
            input_message_id=input_message_id,
            status="completed",
            mode="contract_seed",
            trace_id=context.trace_id,
            assistant_content=_assistant_content(prompt, channel),
            created_at=now,
            completed_at=now,
            idempotency_key=idempotency_key,
            metadata={**metadata, "channel": channel},
            narration_steps=[
                {
                    "label": "demande_recue",
                    "status": "complete",
                    "visible": True,
                },
                {
                    "label": "reponse_contractuelle",
                    "status": "complete",
                    "visible": True,
                },
            ],
            actions=[],
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


def _assistant_content(prompt: str, channel: str) -> str:
    normalized_prompt = " ".join(prompt.split())[:180]
    return (
        "Bob a pris en charge la demande dans le runtime CDE. "
        "Cette reponse contractuelle confirme le chemin Bob Chat -> Conversation -> Runtime; "
        f"le branchement provider/memoire viendra dans la prochaine boucle. Canal: {channel}. "
        f"Demande: {normalized_prompt}"
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
