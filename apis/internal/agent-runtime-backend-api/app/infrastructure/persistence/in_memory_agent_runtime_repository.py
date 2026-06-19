"""In-memory Agent Runtime repository for tests."""

from __future__ import annotations

from app.domain import AgentConfirmation, AgentRun


class InMemoryAgentRuntimeRepository:
    def __init__(self) -> None:
        self.runs: dict[str, AgentRun] = {}
        self.confirmations: dict[str, AgentConfirmation] = {}

    def create_run(self, *, run: AgentRun) -> AgentRun:
        self.runs[run.id] = run
        return run

    def get_run(self, *, run_id: str, tenant_id: str, user_id: str) -> AgentRun | None:
        run = self.runs.get(run_id)
        if not run or run.tenant_id != tenant_id or run.user_id != user_id:
            return None
        return run

    def get_run_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> AgentRun | None:
        for run in self.runs.values():
            if (
                run.tenant_id == tenant_id
                and run.user_id == user_id
                and run.idempotency_key == idempotency_key
            ):
                return run
        return None

    def update_run(self, *, run: AgentRun) -> AgentRun:
        self.runs[run.id] = run
        return run

    def get_confirmation(
        self,
        *,
        confirmation_id: str,
        run_id: str,
        tenant_id: str,
        user_id: str,
    ) -> AgentConfirmation | None:
        confirmation = self.confirmations.get(confirmation_id)
        if (
            not confirmation
            or confirmation.run_id != run_id
            or confirmation.tenant_id != tenant_id
            or confirmation.user_id != user_id
        ):
            return None
        return confirmation

    def update_confirmation(self, *, confirmation: AgentConfirmation) -> AgentConfirmation:
        self.confirmations[confirmation.id] = confirmation
        return confirmation
