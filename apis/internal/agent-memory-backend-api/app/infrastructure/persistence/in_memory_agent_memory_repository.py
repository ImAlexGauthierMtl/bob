"""In-memory Agent Memory repository for tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from app.domain import MemoryEntry, MemoryJournalEntry, MemoryScope, VectorIndexJob, VectorIndexRecord


class InMemoryAgentMemoryRepository:
    def __init__(self) -> None:
        self.entries: dict[str, MemoryEntry] = {}
        self.journal: dict[str, MemoryJournalEntry] = {}
        self.vector_jobs: dict[str, VectorIndexJob] = {}
        self.vector_records: dict[str, VectorIndexRecord] = {}

    def count_entries(self, *, tenant_id: str, user_id: str) -> int:
        return len(
            [
                entry
                for entry in self.entries.values()
                if entry.tenant_id == tenant_id
                and entry.user_id == user_id
                and entry.scope_type == MemoryScope.PRIVATE_USER
            ]
        )

    def count_organization_entries(self, *, tenant_id: str) -> int:
        return len(
            [
                entry
                for entry in self.entries.values()
                if entry.tenant_id == tenant_id and entry.scope_type == MemoryScope.ORGANIZATION
            ]
        )

    def count_journal_entries(self, *, tenant_id: str, user_id: str) -> int:
        return len(
            [
                entry
                for entry in self.journal.values()
                if entry.tenant_id == tenant_id and entry.user_id == user_id
            ]
        )

    def latest_event(self, *, tenant_id: str, user_id: str) -> datetime | None:
        events = [
            entry.created_at
            for entry in self.entries.values()
            if entry.tenant_id == tenant_id and entry.user_id == user_id
        ] + [
            entry.created_at
            for entry in self.journal.values()
            if entry.tenant_id == tenant_id and entry.user_id == user_id
        ]
        return max(events) if events else None

    def get_entry_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
        scope_type: str,
    ) -> MemoryEntry | None:
        for entry in self.entries.values():
            if (
                entry.tenant_id == tenant_id
                and entry.user_id == user_id
                and entry.scope_type == scope_type
                and entry.idempotency_key == idempotency_key
            ):
                return entry
        return None

    def create_entry(self, *, entry: MemoryEntry) -> MemoryEntry:
        self.entries[entry.id] = entry
        return entry

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
        normalized = query.lower()
        results = []
        now = datetime.now(timezone.utc)
        for entry in self.entries.values():
            if entry.tenant_id != tenant_id or entry.scope_type != scope_type:
                continue
            if user_id is not None and entry.user_id != user_id:
                continue
            if memory_types and entry.memory_type not in memory_types:
                continue
            if not include_sensitive and entry.sensitivity == "client_confidential":
                continue
            if entry.expires_at and entry.expires_at < now:
                continue
            haystack = f"{entry.title} {entry.content}".lower()
            if normalized and normalized not in haystack:
                continue
            results.append(entry)
        return results[:limit]

    def get_entry(self, *, entry_id: str, tenant_id: str) -> MemoryEntry | None:
        entry = self.entries.get(entry_id)
        if not entry or entry.tenant_id != tenant_id:
            return None
        return entry

    def get_entries_by_ids(
        self,
        *,
        tenant_id: str,
        entry_ids: tuple[str, ...],
    ) -> list[MemoryEntry]:
        requested = set(entry_ids)
        return [
            entry
            for entry in self.entries.values()
            if entry.tenant_id == tenant_id and entry.id in requested
        ]

    def get_journal_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> MemoryJournalEntry | None:
        for entry in self.journal.values():
            if (
                entry.tenant_id == tenant_id
                and entry.user_id == user_id
                and entry.idempotency_key == idempotency_key
            ):
                return entry
        return None

    def create_journal_entry(self, *, entry: MemoryJournalEntry) -> MemoryJournalEntry:
        self.journal[entry.id] = entry
        return entry

    def get_vector_job_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> VectorIndexJob | None:
        for job in self.vector_jobs.values():
            if (
                job.tenant_id == tenant_id
                and job.user_id == user_id
                and job.idempotency_key == idempotency_key
            ):
                return job
        return None

    def create_vector_job(self, *, job: VectorIndexJob) -> VectorIndexJob:
        self.vector_jobs[job.id] = job
        return job

    def get_vector_job(self, *, job_id: str, tenant_id: str) -> VectorIndexJob | None:
        job = self.vector_jobs.get(job_id)
        if not job or job.tenant_id != tenant_id:
            return None
        return job

    def update_vector_job(self, *, job: VectorIndexJob) -> VectorIndexJob:
        self.vector_jobs[job.id] = job
        return job

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
        results = []
        for entry in sorted(self.entries.values(), key=lambda item: item.id):
            if entry.tenant_id != tenant_id or entry.scope_type != scope_type:
                continue
            if user_id is not None and entry.user_id != user_id:
                continue
            if source_ref and entry.id != source_ref:
                continue
            if entry.status != "active":
                continue
            if entry.expires_at and entry.expires_at < now:
                continue
            results.append(entry)
        return results[:limit]

    def get_vector_records_for_job(self, *, tenant_id: str, job_id: str) -> list[VectorIndexRecord]:
        return [
            record
            for record in sorted(self.vector_records.values(), key=lambda item: item.source_id)
            if record.tenant_id == tenant_id and record.job_id == job_id
        ]

    def get_vector_records_by_vector_ids(
        self,
        *,
        tenant_id: str,
        vector_ids: tuple[str, ...],
    ) -> list[VectorIndexRecord]:
        requested = set(vector_ids)
        return [
            record
            for record in self.vector_records.values()
            if record.tenant_id == tenant_id and record.vector_id in requested
        ]

    def create_vector_records(self, *, records: list[VectorIndexRecord]) -> list[VectorIndexRecord]:
        created = []
        for record in records:
            existing = next(
                (
                    item
                    for item in self.vector_records.values()
                    if item.tenant_id == record.tenant_id
                    and item.job_id == record.job_id
                    and item.source_id == record.source_id
                ),
                None,
            )
            if existing:
                created.append(existing)
                continue
            self.vector_records[record.id] = record
            created.append(record)
        return created

    def update_vector_records_status_for_job(
        self,
        *,
        tenant_id: str,
        job_id: str,
        status: str,
    ) -> int:
        updated = 0
        for record_id, record in list(self.vector_records.items()):
            if record.tenant_id == tenant_id and record.job_id == job_id:
                self.vector_records[record_id] = replace(record, index_status=status)
                updated += 1
        return updated
