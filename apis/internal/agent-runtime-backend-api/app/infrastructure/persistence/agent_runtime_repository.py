"""SQLAlchemy repository for Agent Runtime data."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.domain import AgentConfirmation, AgentRun
from app.infrastructure.persistence.models.agent_runtime import (
    AgentConfirmationModel,
    AgentRunModel,
)


class AgentRuntimeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_run(self, *, run: AgentRun) -> AgentRun:
        model = AgentRunModel(
            id=run.id,
            tenant_id=run.tenant_id,
            user_id=run.user_id,
            session_id=run.session_id,
            input_message_id=run.input_message_id,
            status=run.status,
            mode=run.mode,
            trace_id=run.trace_id,
            assistant_content=run.assistant_content,
            metadata_=run.metadata,
            narration_steps=run.narration_steps,
            actions=run.actions,
            artifacts=run.artifacts,
            idempotency_key=run.idempotency_key,
            created_at=run.created_at,
            completed_at=run.completed_at,
            cancelled_at=run.cancelled_at,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return _run_from_model(model)

    def get_run(
        self,
        *,
        run_id: str,
        tenant_id: str,
        user_id: str,
    ) -> Optional[AgentRun]:
        model = (
            self.db.query(AgentRunModel)
            .filter(
                AgentRunModel.id == run_id,
                AgentRunModel.tenant_id == tenant_id,
                AgentRunModel.user_id == user_id,
            )
            .one_or_none()
        )
        return _run_from_model(model) if model else None

    def get_run_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> Optional[AgentRun]:
        model = (
            self.db.query(AgentRunModel)
            .filter(
                AgentRunModel.tenant_id == tenant_id,
                AgentRunModel.user_id == user_id,
                AgentRunModel.idempotency_key == idempotency_key,
            )
            .one_or_none()
        )
        return _run_from_model(model) if model else None

    def update_run(self, *, run: AgentRun) -> AgentRun:
        model = self.db.query(AgentRunModel).filter(AgentRunModel.id == run.id).one()
        model.status = run.status
        model.cancelled_at = run.cancelled_at
        self.db.commit()
        self.db.refresh(model)
        return _run_from_model(model)

    def get_confirmation(
        self,
        *,
        confirmation_id: str,
        run_id: str,
        tenant_id: str,
        user_id: str,
    ) -> Optional[AgentConfirmation]:
        model = (
            self.db.query(AgentConfirmationModel)
            .filter(
                AgentConfirmationModel.id == confirmation_id,
                AgentConfirmationModel.run_id == run_id,
                AgentConfirmationModel.tenant_id == tenant_id,
                AgentConfirmationModel.user_id == user_id,
            )
            .one_or_none()
        )
        return _confirmation_from_model(model) if model else None

    def update_confirmation(self, *, confirmation: AgentConfirmation) -> AgentConfirmation:
        model = (
            self.db.query(AgentConfirmationModel)
            .filter(AgentConfirmationModel.id == confirmation.id)
            .one()
        )
        model.status = confirmation.status
        model.resolved_at = confirmation.resolved_at
        self.db.commit()
        self.db.refresh(model)
        return _confirmation_from_model(model)


def _run_from_model(model: AgentRunModel) -> AgentRun:
    return AgentRun(
        id=model.id,
        tenant_id=model.tenant_id,
        user_id=model.user_id,
        session_id=model.session_id,
        input_message_id=model.input_message_id,
        status=model.status,
        mode=model.mode,
        trace_id=model.trace_id,
        assistant_content=model.assistant_content,
        created_at=model.created_at,
        completed_at=model.completed_at,
        cancelled_at=model.cancelled_at,
        idempotency_key=model.idempotency_key,
        metadata=model.metadata_ or {},
        narration_steps=model.narration_steps or [],
        actions=model.actions or [],
        artifacts=model.artifacts or [],
    )


def _confirmation_from_model(model: AgentConfirmationModel) -> AgentConfirmation:
    return AgentConfirmation(
        id=model.id,
        run_id=model.run_id,
        tenant_id=model.tenant_id,
        user_id=model.user_id,
        status=model.status,
        label=model.label,
        created_at=model.created_at,
        resolved_at=model.resolved_at,
    )
