"""SQLAlchemy repository for Agent Memory data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.domain import MemoryEntry, MemoryJournalEntry, MemoryScope, VectorIndexJob, VectorIndexRecord
from app.infrastructure.persistence.models.agent_memory import (
    MemoryEntryModel,
    MemoryJournalModel,
    VectorIndexJobModel,
    VectorIndexRecordModel,
)


class AgentMemoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def count_entries(self, *, tenant_id: str, user_id: str) -> int:
        return (
            self.db.query(MemoryEntryModel)
            .filter(
                MemoryEntryModel.tenant_id == tenant_id,
                MemoryEntryModel.user_id == user_id,
                MemoryEntryModel.scope_type == MemoryScope.PRIVATE_USER,
            )
            .count()
        )

    def count_organization_entries(self, *, tenant_id: str) -> int:
        return (
            self.db.query(MemoryEntryModel)
            .filter(
                MemoryEntryModel.tenant_id == tenant_id,
                MemoryEntryModel.scope_type == MemoryScope.ORGANIZATION,
            )
            .count()
        )

    def count_journal_entries(self, *, tenant_id: str, user_id: str) -> int:
        return (
            self.db.query(MemoryJournalModel)
            .filter(
                MemoryJournalModel.tenant_id == tenant_id,
                MemoryJournalModel.user_id == user_id,
            )
            .count()
        )

    def latest_event(self, *, tenant_id: str, user_id: str) -> Optional[datetime]:
        latest_entry = (
            self.db.query(MemoryEntryModel)
            .filter(MemoryEntryModel.tenant_id == tenant_id, MemoryEntryModel.user_id == user_id)
            .order_by(MemoryEntryModel.created_at.desc())
            .first()
        )
        latest_journal = (
            self.db.query(MemoryJournalModel)
            .filter(MemoryJournalModel.tenant_id == tenant_id, MemoryJournalModel.user_id == user_id)
            .order_by(MemoryJournalModel.created_at.desc())
            .first()
        )
        events = [
            model.created_at
            for model in (latest_entry, latest_journal)
            if model is not None and model.created_at is not None
        ]
        return max(events) if events else None

    def get_entry_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
        scope_type: str,
    ) -> Optional[MemoryEntry]:
        model = (
            self.db.query(MemoryEntryModel)
            .filter(
                MemoryEntryModel.tenant_id == tenant_id,
                MemoryEntryModel.user_id == user_id,
                MemoryEntryModel.scope_type == scope_type,
                MemoryEntryModel.idempotency_key == idempotency_key,
            )
            .one_or_none()
        )
        return _entry_from_model(model) if model else None

    def create_entry(self, *, entry: MemoryEntry) -> MemoryEntry:
        model = MemoryEntryModel(
            id=entry.id,
            tenant_id=entry.tenant_id,
            user_id=entry.user_id,
            scope_type=entry.scope_type,
            memory_type=entry.memory_type,
            title=entry.title,
            content=entry.content,
            source_type=entry.source_type,
            source_ref=entry.source_ref,
            sensitivity=entry.sensitivity,
            status=entry.status,
            trace_id=entry.trace_id,
            verified_at=entry.verified_at,
            created_at=entry.created_at,
            expires_at=entry.expires_at,
            idempotency_key=entry.idempotency_key,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return _entry_from_model(model)

    def search_entries(
        self,
        *,
        tenant_id: str,
        user_id: str | None,
        scope_type: str,
        query: str,
        memory_types: tuple[str, ...],
        limit: int,
        include_sensitive: bool,
    ) -> list[MemoryEntry]:
        now = datetime.now(timezone.utc)
        query_filter = f"%{query}%"
        q = self.db.query(MemoryEntryModel).filter(
            MemoryEntryModel.tenant_id == tenant_id,
            MemoryEntryModel.scope_type == scope_type,
            MemoryEntryModel.status == "active",
            or_(MemoryEntryModel.expires_at.is_(None), MemoryEntryModel.expires_at > now),
            or_(MemoryEntryModel.title.ilike(query_filter), MemoryEntryModel.content.ilike(query_filter)),
        )
        if user_id is not None:
            q = q.filter(MemoryEntryModel.user_id == user_id)
        if memory_types:
            q = q.filter(MemoryEntryModel.memory_type.in_(memory_types))
        if not include_sensitive:
            q = q.filter(MemoryEntryModel.sensitivity != "client_confidential")
        return [_entry_from_model(model) for model in q.order_by(MemoryEntryModel.created_at.desc()).limit(limit)]

    def get_entry(self, *, entry_id: str, tenant_id: str) -> Optional[MemoryEntry]:
        model = (
            self.db.query(MemoryEntryModel)
            .filter(MemoryEntryModel.id == entry_id, MemoryEntryModel.tenant_id == tenant_id)
            .one_or_none()
        )
        return _entry_from_model(model) if model else None

    def get_entries_by_ids(
        self,
        *,
        tenant_id: str,
        entry_ids: tuple[str, ...],
    ) -> list[MemoryEntry]:
        if not entry_ids:
            return []
        models = (
            self.db.query(MemoryEntryModel)
            .filter(
                MemoryEntryModel.tenant_id == tenant_id,
                MemoryEntryModel.id.in_(entry_ids),
            )
            .all()
        )
        return [_entry_from_model(model) for model in models]

    def get_journal_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> Optional[MemoryJournalEntry]:
        model = (
            self.db.query(MemoryJournalModel)
            .filter(
                MemoryJournalModel.tenant_id == tenant_id,
                MemoryJournalModel.user_id == user_id,
                MemoryJournalModel.idempotency_key == idempotency_key,
            )
            .one_or_none()
        )
        return _journal_from_model(model) if model else None

    def create_journal_entry(self, *, entry: MemoryJournalEntry) -> MemoryJournalEntry:
        model = MemoryJournalModel(
            id=entry.id,
            tenant_id=entry.tenant_id,
            user_id=entry.user_id,
            request_summary=entry.request_summary,
            actions_taken=entry.actions_taken,
            sources_checked=entry.sources_checked,
            result=entry.result,
            next_step=entry.next_step,
            sensitivity=entry.sensitivity,
            trace_id=entry.trace_id,
            created_at=entry.created_at,
            idempotency_key=entry.idempotency_key,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return _journal_from_model(model)

    def get_vector_job_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> Optional[VectorIndexJob]:
        model = (
            self.db.query(VectorIndexJobModel)
            .filter(
                VectorIndexJobModel.tenant_id == tenant_id,
                VectorIndexJobModel.user_id == user_id,
                VectorIndexJobModel.idempotency_key == idempotency_key,
            )
            .one_or_none()
        )
        return _vector_job_from_model(model) if model else None

    def create_vector_job(self, *, job: VectorIndexJob) -> VectorIndexJob:
        model = VectorIndexJobModel(
            id=job.id,
            tenant_id=job.tenant_id,
            user_id=job.user_id,
            collection=job.collection,
            shadow_collection=job.shadow_collection,
            scope_type=job.scope_type,
            status=job.status,
            trace_id=job.trace_id,
            embedding_model=job.embedding_model,
            embedding_version=job.embedding_version,
            source_ref=job.source_ref,
            dry_run=job.dry_run,
            requested_at=job.requested_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            rollback_of_job_id=job.rollback_of_job_id,
            idempotency_key=job.idempotency_key,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return _vector_job_from_model(model)

    def get_vector_job(self, *, job_id: str, tenant_id: str) -> Optional[VectorIndexJob]:
        model = (
            self.db.query(VectorIndexJobModel)
            .filter(VectorIndexJobModel.id == job_id, VectorIndexJobModel.tenant_id == tenant_id)
            .one_or_none()
        )
        return _vector_job_from_model(model) if model else None

    def update_vector_job(self, *, job: VectorIndexJob) -> VectorIndexJob:
        model = self.db.query(VectorIndexJobModel).filter(VectorIndexJobModel.id == job.id).one()
        model.status = job.status
        model.started_at = job.started_at
        model.completed_at = job.completed_at
        model.rollback_of_job_id = job.rollback_of_job_id
        model.error_message = job.error_message
        self.db.commit()
        self.db.refresh(model)
        return _vector_job_from_model(model)

    def list_indexable_entries(
        self,
        *,
        tenant_id: str,
        user_id: str | None,
        scope_type: str,
        source_ref: str | None,
        limit: int,
    ) -> list[MemoryEntry]:
        now = datetime.now(timezone.utc)
        q = self.db.query(MemoryEntryModel).filter(
            MemoryEntryModel.tenant_id == tenant_id,
            MemoryEntryModel.scope_type == scope_type,
            MemoryEntryModel.status == "active",
            or_(MemoryEntryModel.expires_at.is_(None), MemoryEntryModel.expires_at > now),
        )
        if user_id is not None:
            q = q.filter(MemoryEntryModel.user_id == user_id)
        if source_ref:
            q = q.filter(MemoryEntryModel.id == source_ref)
        return [_entry_from_model(model) for model in q.order_by(MemoryEntryModel.id.asc()).limit(limit)]

    def get_vector_records_for_job(self, *, tenant_id: str, job_id: str) -> list[VectorIndexRecord]:
        models = (
            self.db.query(VectorIndexRecordModel)
            .filter(
                VectorIndexRecordModel.tenant_id == tenant_id,
                VectorIndexRecordModel.job_id == job_id,
            )
            .order_by(VectorIndexRecordModel.source_id.asc())
            .all()
        )
        return [_vector_record_from_model(model) for model in models]

    def get_vector_records_by_vector_ids(
        self,
        *,
        tenant_id: str,
        vector_ids: tuple[str, ...],
    ) -> list[VectorIndexRecord]:
        if not vector_ids:
            return []
        models = (
            self.db.query(VectorIndexRecordModel)
            .filter(
                VectorIndexRecordModel.tenant_id == tenant_id,
                VectorIndexRecordModel.vector_id.in_(vector_ids),
            )
            .all()
        )
        return [_vector_record_from_model(model) for model in models]

    def create_vector_records(self, *, records: list[VectorIndexRecord]) -> list[VectorIndexRecord]:
        created: list[VectorIndexRecord] = []
        for record in records:
            existing = (
                self.db.query(VectorIndexRecordModel)
                .filter(
                    VectorIndexRecordModel.tenant_id == record.tenant_id,
                    VectorIndexRecordModel.job_id == record.job_id,
                    VectorIndexRecordModel.source_id == record.source_id,
                )
                .one_or_none()
            )
            if existing:
                created.append(_vector_record_from_model(existing))
                continue
            model = VectorIndexRecordModel(
                id=record.id,
                tenant_id=record.tenant_id,
                user_id=record.user_id,
                scope_type=record.scope_type,
                scope_key=record.scope_key,
                source_table=record.source_table,
                source_id=record.source_id,
                collection=record.collection,
                shadow_collection=record.shadow_collection,
                vector_id=record.vector_id,
                index_status=record.index_status,
                content_hash=record.content_hash,
                embedding_model=record.embedding_model,
                embedding_version=record.embedding_version,
                trace_id=record.trace_id,
                created_at=record.created_at,
                job_id=record.job_id,
            )
            self.db.add(model)
            created.append(record)
        self.db.commit()
        return created

    def update_vector_records_status_for_job(
        self,
        *,
        tenant_id: str,
        job_id: str,
        status: str,
    ) -> int:
        updated = (
            self.db.query(VectorIndexRecordModel)
            .filter(
                VectorIndexRecordModel.tenant_id == tenant_id,
                VectorIndexRecordModel.job_id == job_id,
            )
            .update({VectorIndexRecordModel.index_status: status}, synchronize_session=False)
        )
        self.db.commit()
        return int(updated)


def _entry_from_model(model: MemoryEntryModel) -> MemoryEntry:
    return MemoryEntry(
        id=model.id,
        tenant_id=model.tenant_id,
        user_id=model.user_id,
        scope_type=model.scope_type,
        memory_type=model.memory_type,
        title=model.title,
        content=model.content,
        source_type=model.source_type,
        source_ref=model.source_ref,
        sensitivity=model.sensitivity,
        status=model.status,
        trace_id=model.trace_id,
        verified_at=model.verified_at,
        created_at=model.created_at,
        expires_at=model.expires_at,
        idempotency_key=model.idempotency_key,
    )


def _journal_from_model(model: MemoryJournalModel) -> MemoryJournalEntry:
    return MemoryJournalEntry(
        id=model.id,
        tenant_id=model.tenant_id,
        user_id=model.user_id,
        request_summary=model.request_summary,
        actions_taken=model.actions_taken,
        sources_checked=model.sources_checked,
        result=model.result,
        next_step=model.next_step,
        sensitivity=model.sensitivity,
        trace_id=model.trace_id,
        created_at=model.created_at,
        idempotency_key=model.idempotency_key,
    )


def _vector_job_from_model(model: VectorIndexJobModel) -> VectorIndexJob:
    return VectorIndexJob(
        id=model.id,
        tenant_id=model.tenant_id,
        user_id=model.user_id,
        collection=model.collection,
        shadow_collection=model.shadow_collection,
        scope_type=model.scope_type,
        status=model.status,
        trace_id=model.trace_id,
        embedding_model=model.embedding_model,
        embedding_version=model.embedding_version,
        requested_at=model.requested_at,
        source_ref=model.source_ref,
        dry_run=model.dry_run,
        started_at=model.started_at,
        completed_at=model.completed_at,
        error_message=model.error_message,
        rollback_of_job_id=model.rollback_of_job_id,
        idempotency_key=model.idempotency_key,
    )


def _vector_record_from_model(model: VectorIndexRecordModel) -> VectorIndexRecord:
    return VectorIndexRecord(
        id=model.id,
        tenant_id=model.tenant_id,
        user_id=model.user_id,
        scope_type=model.scope_type,
        scope_key=model.scope_key,
        source_table=model.source_table,
        source_id=model.source_id,
        collection=model.collection,
        shadow_collection=model.shadow_collection,
        vector_id=model.vector_id,
        index_status=model.index_status,
        content_hash=model.content_hash,
        embedding_model=model.embedding_model,
        embedding_version=model.embedding_version,
        trace_id=model.trace_id,
        created_at=model.created_at,
        job_id=model.job_id,
    )
