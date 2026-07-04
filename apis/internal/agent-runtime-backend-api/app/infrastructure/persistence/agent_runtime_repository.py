"""SQLAlchemy repository for Agent Runtime data."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.domain import AgentConfirmation, AgentRun, RuntimeCatalogItem
from app.infrastructure.persistence.models.agent_runtime import (
    AgentConfirmationModel,
    AgentRunModel,
    RuntimeCatalogItemModel,
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

    def create_run_with_confirmations(
        self,
        *,
        run: AgentRun,
        confirmations: list[AgentConfirmation],
    ) -> AgentRun:
        run_model = AgentRunModel(
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
        try:
            self.db.add(run_model)
            self.db.flush()
            for confirmation in confirmations:
                self.db.add(
                    AgentConfirmationModel(
                        id=confirmation.id,
                        run_id=confirmation.run_id,
                        tenant_id=confirmation.tenant_id,
                        user_id=confirmation.user_id,
                        status=confirmation.status,
                        label=confirmation.label,
                        created_at=confirmation.created_at,
                        resolved_at=confirmation.resolved_at,
                    )
                )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(run_model)
        return _run_from_model(run_model)

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

    def list_catalog_items(
        self,
        *,
        tenant_id: str,
        user_id: str,
        collection: str,
    ) -> list[RuntimeCatalogItem]:
        models = (
            self.db.query(RuntimeCatalogItemModel)
            .filter(
                RuntimeCatalogItemModel.tenant_id == tenant_id,
                RuntimeCatalogItemModel.collection == collection,
            )
            .order_by(RuntimeCatalogItemModel.created_at.asc(), RuntimeCatalogItemModel.id.asc())
            .all()
        )
        return [_catalog_item_from_model(model) for model in models]

    def list_user_catalog_items(
        self,
        *,
        tenant_id: str,
        user_id: str,
        collection: str,
    ) -> list[RuntimeCatalogItem]:
        models = (
            self.db.query(RuntimeCatalogItemModel)
            .filter(
                RuntimeCatalogItemModel.tenant_id == tenant_id,
                RuntimeCatalogItemModel.user_id == user_id,
                RuntimeCatalogItemModel.collection == collection,
            )
            .order_by(RuntimeCatalogItemModel.created_at.asc(), RuntimeCatalogItemModel.id.asc())
            .all()
        )
        return [_catalog_item_from_model(model) for model in models]

    def get_catalog_item(
        self,
        *,
        item_id: str,
        tenant_id: str,
        collection: str,
        user_id: str | None = None,
    ) -> RuntimeCatalogItem | None:
        query = self.db.query(RuntimeCatalogItemModel).filter(
            RuntimeCatalogItemModel.id == item_id,
            RuntimeCatalogItemModel.tenant_id == tenant_id,
            RuntimeCatalogItemModel.collection == collection,
        )
        if user_id is not None:
            query = query.filter(RuntimeCatalogItemModel.user_id == user_id)
        model = query.one_or_none()
        return _catalog_item_from_model(model) if model else None

    def get_catalog_item_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        collection: str,
        idempotency_key: str,
    ) -> RuntimeCatalogItem | None:
        model = (
            self.db.query(RuntimeCatalogItemModel)
            .filter(
                RuntimeCatalogItemModel.tenant_id == tenant_id,
                RuntimeCatalogItemModel.user_id == user_id,
                RuntimeCatalogItemModel.collection == collection,
                RuntimeCatalogItemModel.idempotency_key == idempotency_key,
            )
            .one_or_none()
        )
        return _catalog_item_from_model(model) if model else None

    def create_catalog_item(self, *, item: RuntimeCatalogItem) -> RuntimeCatalogItem:
        model = RuntimeCatalogItemModel(
            id=item.id,
            tenant_id=item.tenant_id,
            user_id=item.user_id,
            collection=item.collection,
            name=item.name,
            payload=item.payload,
            payload_hash=item.payload_hash,
            idempotency_key=item.idempotency_key,
            created_at=item.created_at,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return _catalog_item_from_model(model)

    def upsert_catalog_item(self, *, item: RuntimeCatalogItem) -> RuntimeCatalogItem:
        model = (
            self.db.query(RuntimeCatalogItemModel)
            .filter(
                RuntimeCatalogItemModel.id == item.id,
                RuntimeCatalogItemModel.tenant_id == item.tenant_id,
                RuntimeCatalogItemModel.collection == item.collection,
            )
            .one_or_none()
        )
        if model is None:
            return self.create_catalog_item(item=item)
        model.user_id = item.user_id
        model.name = item.name
        model.payload = item.payload
        model.payload_hash = item.payload_hash
        model.idempotency_key = item.idempotency_key
        self.db.commit()
        self.db.refresh(model)
        return _catalog_item_from_model(model)


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


def _catalog_item_from_model(model: RuntimeCatalogItemModel) -> RuntimeCatalogItem:
    return RuntimeCatalogItem(
        id=model.id,
        tenant_id=model.tenant_id,
        user_id=model.user_id,
        collection=model.collection,
        name=model.name,
        payload=model.payload or {},
        payload_hash=model.payload_hash,
        idempotency_key=model.idempotency_key,
        created_at=model.created_at,
    )
