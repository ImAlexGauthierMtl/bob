"""Agent Memory application use cases."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from typing import Optional, Protocol
from uuid import uuid4

from app.domain import (
    InternalContext,
    MemoryEntry,
    MemoryError,
    MemoryForbiddenError,
    MemoryJournalEntry,
    MemoryNotFoundError,
    MemoryScope,
    VectorIndexJob,
    VectorIndexRecord,
    VectorRevalidationMatch,
)


VECTOR_COLLECTION_SCOPES = {
    "bob_private_memory_chunks_v1": MemoryScope.PRIVATE_USER,
    "bob_organization_knowledge_chunks_v1": MemoryScope.ORGANIZATION,
    "bob_shared_skill_chunks_v1": MemoryScope.SHARED_CLEAN,
}
ACTIVE_VECTOR_RECORD_STATUSES = {"indexed"}
RAG_ALLOWED_SENSITIVITIES = {"internal", "private_user", "public"}


class AgentMemoryRepositoryPort(Protocol):
    def count_entries(self, *, tenant_id: str, user_id: str) -> int:
        ...

    def count_organization_entries(self, *, tenant_id: str) -> int:
        ...

    def count_journal_entries(self, *, tenant_id: str, user_id: str) -> int:
        ...

    def latest_event(self, *, tenant_id: str, user_id: str) -> Optional[datetime]:
        ...

    def get_entry_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
        scope_type: str,
    ) -> Optional[MemoryEntry]:
        ...

    def create_entry(self, *, entry: MemoryEntry) -> MemoryEntry:
        ...

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
        ...

    def get_entry(self, *, entry_id: str, tenant_id: str) -> Optional[MemoryEntry]:
        ...

    def get_entries_by_ids(
        self,
        *,
        tenant_id: str,
        entry_ids: tuple[str, ...],
    ) -> list[MemoryEntry]:
        ...

    def get_journal_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> Optional[MemoryJournalEntry]:
        ...

    def create_journal_entry(self, *, entry: MemoryJournalEntry) -> MemoryJournalEntry:
        ...

    def get_vector_job_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> Optional[VectorIndexJob]:
        ...

    def create_vector_job(self, *, job: VectorIndexJob) -> VectorIndexJob:
        ...

    def get_vector_job(self, *, job_id: str, tenant_id: str) -> Optional[VectorIndexJob]:
        ...

    def update_vector_job(self, *, job: VectorIndexJob) -> VectorIndexJob:
        ...

    def list_indexable_entries(
        self,
        *,
        tenant_id: str,
        user_id: str | None,
        scope_type: str,
        source_ref: str | None,
        limit: int,
    ) -> list[MemoryEntry]:
        ...

    def get_vector_records_for_job(self, *, tenant_id: str, job_id: str) -> list[VectorIndexRecord]:
        ...

    def get_vector_records_by_vector_ids(
        self,
        *,
        tenant_id: str,
        vector_ids: tuple[str, ...],
    ) -> list[VectorIndexRecord]:
        ...

    def create_vector_records(self, *, records: list[VectorIndexRecord]) -> list[VectorIndexRecord]:
        ...

    def update_vector_records_status_for_job(
        self,
        *,
        tenant_id: str,
        job_id: str,
        status: str,
    ) -> int:
        ...


class AgentMemoryUseCases:
    def __init__(self, *, repo: AgentMemoryRepositoryPort) -> None:
        self.repo = repo

    def authorize_rag_context(self, *, context: InternalContext) -> None:
        _require_rag_permission(context)

    async def status(self, *, context: InternalContext) -> dict[str, object]:
        return {
            "tenant_id": context.tenant_id,
            "user_id": context.user_id,
            "database_status": "available",
            "memory_entries": self.repo.count_entries(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
            ),
            "organization_entries": self.repo.count_organization_entries(
                tenant_id=context.tenant_id,
            ),
            "journal_entries": self.repo.count_journal_entries(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
            ),
            "last_event": self.repo.latest_event(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
            ),
            "isolation_enforced": True,
        }

    async def record_private_entry(
        self,
        *,
        context: InternalContext,
        memory_type: str,
        title: str,
        content: str,
        source_type: str,
        source_ref: str,
        sensitivity: str,
        verified_at: datetime,
        expires_at: datetime | None,
        idempotency_key: str,
    ) -> MemoryEntry:
        _refuse_secret(sensitivity=sensitivity, content=content)
        existing = self.repo.get_entry_by_idempotency_key(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            idempotency_key=idempotency_key,
            scope_type=MemoryScope.PRIVATE_USER,
        )
        if existing:
            return existing
        entry = MemoryEntry(
            id=f"mem_{uuid4().hex}",
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            scope_type=MemoryScope.PRIVATE_USER,
            memory_type=memory_type,
            title=title,
            content=content,
            source_type=source_type,
            source_ref=source_ref,
            sensitivity=sensitivity,
            status="active",
            trace_id=context.trace_id,
            verified_at=verified_at,
            created_at=_utc_now(),
            expires_at=expires_at,
            idempotency_key=idempotency_key,
        )
        return self.repo.create_entry(entry=entry)

    async def record_organization_entry(
        self,
        *,
        context: InternalContext,
        memory_type: str,
        title: str,
        content: str,
        source_type: str,
        source_ref: str,
        sensitivity: str,
        verified_at: datetime,
        expires_at: datetime | None,
        idempotency_key: str,
    ) -> MemoryEntry:
        _require_organization_permission(context, "agent_memory.organization.write")
        _refuse_secret(sensitivity=sensitivity, content=content)
        existing = self.repo.get_entry_by_idempotency_key(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            idempotency_key=idempotency_key,
            scope_type=MemoryScope.ORGANIZATION,
        )
        if existing:
            return existing
        entry = MemoryEntry(
            id=f"mem_{uuid4().hex}",
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            scope_type=MemoryScope.ORGANIZATION,
            memory_type=memory_type,
            title=title,
            content=content,
            source_type=source_type,
            source_ref=source_ref,
            sensitivity=sensitivity,
            status="active",
            trace_id=context.trace_id,
            verified_at=verified_at,
            created_at=_utc_now(),
            expires_at=expires_at,
            idempotency_key=idempotency_key,
        )
        return self.repo.create_entry(entry=entry)

    async def search_private(
        self,
        *,
        context: InternalContext,
        query: str,
        memory_types: tuple[str, ...],
        limit: int,
        include_sensitive: bool,
    ) -> list[MemoryEntry]:
        return self.repo.search_entries(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            scope_type=MemoryScope.PRIVATE_USER,
            query=query,
            memory_types=memory_types,
            limit=limit,
            include_sensitive=include_sensitive,
        )

    async def search_organization(
        self,
        *,
        context: InternalContext,
        query: str,
        memory_types: tuple[str, ...],
        limit: int,
        include_sensitive: bool,
    ) -> list[MemoryEntry]:
        _require_organization_permission(context, "agent_memory.organization.search")
        return self.repo.search_entries(
            tenant_id=context.tenant_id,
            user_id=None,
            scope_type=MemoryScope.ORGANIZATION,
            query=query,
            memory_types=memory_types,
            limit=limit,
            include_sensitive=include_sensitive,
        )

    async def readback(self, *, context: InternalContext, entry_id: str) -> MemoryEntry:
        entry = self.repo.get_entry(entry_id=entry_id, tenant_id=context.tenant_id)
        if not entry:
            raise MemoryNotFoundError("memory_entry_not_found")
        if entry.scope_type == MemoryScope.PRIVATE_USER and entry.user_id != context.user_id:
            raise MemoryNotFoundError("memory_entry_not_found")
        if entry.scope_type == MemoryScope.ORGANIZATION:
            _require_organization_permission(context, "agent_memory.organization.search")
        return entry

    async def record_journal(
        self,
        *,
        context: InternalContext,
        request_summary: str,
        actions_taken: str,
        sources_checked: str,
        result: str,
        next_step: str,
        sensitivity: str,
        idempotency_key: str,
    ) -> MemoryJournalEntry:
        _refuse_secret(sensitivity=sensitivity, content=result)
        existing = self.repo.get_journal_by_idempotency_key(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            idempotency_key=idempotency_key,
        )
        if existing:
            return existing
        journal_entry = MemoryJournalEntry(
            id=f"jrnl_{uuid4().hex}",
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            request_summary=request_summary,
            actions_taken=actions_taken,
            sources_checked=sources_checked,
            result=result,
            next_step=next_step,
            sensitivity=sensitivity,
            trace_id=context.trace_id,
            created_at=_utc_now(),
            idempotency_key=idempotency_key,
        )
        return self.repo.create_journal_entry(entry=journal_entry)

    async def create_vector_rebuild_job(
        self,
        *,
        context: InternalContext,
        collection: str,
        scope_type: str | None,
        source_ref: str | None,
        dry_run: bool,
        embedding_model: str,
        embedding_version: str,
        idempotency_key: str,
    ) -> VectorIndexJob:
        _require_vector_permission(context)
        resolved_scope = _resolve_collection_scope(collection=collection, scope_type=scope_type)
        existing = self.repo.get_vector_job_by_idempotency_key(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            idempotency_key=idempotency_key,
        )
        if existing:
            return existing
        job_id = f"vij_{uuid4().hex}"
        job = VectorIndexJob(
            id=job_id,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            collection=collection,
            shadow_collection=f"{collection}__rebuild_{job_id}",
            scope_type=resolved_scope,
            status="queued",
            trace_id=context.trace_id,
            embedding_model=embedding_model,
            embedding_version=embedding_version,
            requested_at=_utc_now(),
            source_ref=source_ref,
            dry_run=dry_run,
            idempotency_key=idempotency_key,
        )
        return self.repo.create_vector_job(job=job)

    async def get_vector_job(self, *, context: InternalContext, job_id: str) -> VectorIndexJob:
        _require_vector_permission(context)
        job = self.repo.get_vector_job(job_id=job_id, tenant_id=context.tenant_id)
        if not job:
            raise MemoryNotFoundError("vector_index_job_not_found")
        if job.scope_type == MemoryScope.PRIVATE_USER and job.user_id != context.user_id:
            raise MemoryNotFoundError("vector_index_job_not_found")
        return job

    async def rollback_vector_job(self, *, context: InternalContext, job_id: str) -> VectorIndexJob:
        job = await self.get_vector_job(context=context, job_id=job_id)
        if job.status == "rolled_back":
            return job
        self.repo.update_vector_records_status_for_job(
            tenant_id=context.tenant_id,
            job_id=job.id,
            status="rolled_back",
        )
        return self.repo.update_vector_job(
            job=replace(
                job,
                status="rolled_back",
                completed_at=_utc_now(),
                rollback_of_job_id=job.id,
            )
        )

    async def prepare_vector_job(
        self,
        *,
        context: InternalContext,
        job_id: str,
        limit: int,
    ) -> tuple[VectorIndexJob, list[VectorIndexRecord]]:
        job = await self.get_vector_job(context=context, job_id=job_id)
        existing_records = self.repo.get_vector_records_for_job(
            tenant_id=context.tenant_id,
            job_id=job.id,
        )
        if existing_records:
            return job, existing_records
        user_id = job.user_id if job.scope_type == MemoryScope.PRIVATE_USER else None
        entries = self.repo.list_indexable_entries(
            tenant_id=context.tenant_id,
            user_id=user_id,
            scope_type=job.scope_type,
            source_ref=job.source_ref,
            limit=limit,
        )
        records = [_record_for_entry(job=job, entry=entry) for entry in entries]
        created_records = [] if job.dry_run else self.repo.create_vector_records(records=records)
        prepared_job = self.repo.update_vector_job(
            job=replace(
                job,
                status="running" if records and not job.dry_run else "queued",
                started_at=job.started_at or _utc_now(),
            )
        )
        return prepared_job, records if job.dry_run else created_records

    async def plan_vector_upsert(
        self,
        *,
        context: InternalContext,
        job_id: str,
        limit: int,
    ) -> tuple[VectorIndexJob, list[VectorIndexRecord]]:
        job = await self.get_vector_job(context=context, job_id=job_id)
        records = self.repo.get_vector_records_for_job(
            tenant_id=context.tenant_id,
            job_id=job.id,
        )
        return job, records[:limit]

    async def revalidate_vector_results(
        self,
        *,
        context: InternalContext,
        collection: str,
        vector_ids: tuple[str, ...],
    ) -> list[VectorRevalidationMatch]:
        _require_vector_permission(context)
        return self._revalidate_vector_results(
            context=context,
            collection=collection,
            vector_ids=vector_ids,
        )

    async def build_rag_context_from_vectors(
        self,
        *,
        context: InternalContext,
        collection: str,
        vector_ids: tuple[str, ...],
        limit: int,
    ) -> tuple[list[VectorRevalidationMatch], list[MemoryEntry]]:
        _require_rag_permission(context)
        matches = self._revalidate_vector_results(
            context=context,
            collection=collection,
            vector_ids=vector_ids,
        )
        accepted_source_ids = tuple(match.source_id for match in matches if match.accepted and match.source_id)
        entries_by_id = {
            entry.id: entry
            for entry in self.repo.get_entries_by_ids(
                tenant_id=context.tenant_id,
                entry_ids=accepted_source_ids,
            )
        }
        rag_matches: list[VectorRevalidationMatch] = []
        entries: list[MemoryEntry] = []
        for match in matches:
            if not match.accepted or not match.source_id:
                rag_matches.append(match)
                continue
            entry = entries_by_id.get(match.source_id)
            if not entry:
                rag_matches.append(replace(match, accepted=False, rejection_code="source_not_found"))
                continue
            if entry.sensitivity not in RAG_ALLOWED_SENSITIVITIES:
                rag_matches.append(replace(match, accepted=False, rejection_code="rag_sensitivity_forbidden"))
                continue
            if len(entries) >= limit:
                rag_matches.append(replace(match, accepted=False, rejection_code="rag_limit_exceeded"))
                continue
            rag_matches.append(match)
            entries.append(entry)
        return rag_matches, entries

    def _revalidate_vector_results(
        self,
        *,
        context: InternalContext,
        collection: str,
        vector_ids: tuple[str, ...],
    ) -> list[VectorRevalidationMatch]:
        _resolve_collection_scope(collection=collection, scope_type=None)
        records_by_vector_id = {
            record.vector_id: record
            for record in self.repo.get_vector_records_by_vector_ids(
                tenant_id=context.tenant_id,
                vector_ids=vector_ids,
            )
        }
        matches: list[VectorRevalidationMatch] = []
        for vector_id in vector_ids:
            record = records_by_vector_id.get(vector_id)
            if not record:
                matches.append(_rejected_vector(vector_id=vector_id, code="vector_record_not_found"))
                continue
            rejection_code = self._vector_record_rejection_code(
                context=context,
                record=record,
                collection=collection,
            )
            matches.append(
                VectorRevalidationMatch(
                    vector_id=vector_id,
                    source_id=record.source_id,
                    scope_type=record.scope_type,
                    index_status=record.index_status,
                    accepted=rejection_code is None,
                    rejection_code=rejection_code,
                )
            )
        return matches

    def _vector_record_rejection_code(
        self,
        *,
        context: InternalContext,
        record: VectorIndexRecord,
        collection: str,
    ) -> str | None:
        if record.collection != collection:
            return "vector_collection_mismatch"
        if record.index_status not in ACTIVE_VECTOR_RECORD_STATUSES:
            return "vector_record_not_indexed"
        if record.scope_type == MemoryScope.PRIVATE_USER and record.user_id != context.user_id:
            return "private_scope_mismatch"
        if record.scope_type == MemoryScope.ORGANIZATION:
            try:
                _require_organization_permission(context, "agent_memory.organization.search")
            except MemoryForbiddenError:
                return "organization_scope_forbidden"
        entry = self.repo.get_entry(entry_id=record.source_id, tenant_id=context.tenant_id)
        if not entry:
            return "source_not_found"
        if entry.status != "active":
            return "source_not_active"
        if entry.expires_at and entry.expires_at < _utc_now():
            return "source_expired"
        return None


def _require_organization_permission(context: InternalContext, permission: str) -> None:
    if permission in context.permissions or "admin" in context.roles:
        return
    raise MemoryForbiddenError("organization_memory_forbidden")


def _require_vector_permission(context: InternalContext) -> None:
    if "agent_memory.vector.manage" in context.permissions or "admin" in context.roles:
        return
    raise MemoryForbiddenError("vector_index_forbidden")


def _require_rag_permission(context: InternalContext) -> None:
    if (
        "agent_memory.rag.search" in context.permissions
        or "agent_memory.private.use" in context.permissions
        or "admin" in context.roles
    ):
        return
    raise MemoryForbiddenError("rag_context_forbidden")


def _rejected_vector(*, vector_id: str, code: str) -> VectorRevalidationMatch:
    return VectorRevalidationMatch(
        vector_id=vector_id,
        source_id=None,
        scope_type=None,
        index_status=None,
        accepted=False,
        rejection_code=code,
    )


def _resolve_collection_scope(*, collection: str, scope_type: str | None) -> str:
    expected_scope = VECTOR_COLLECTION_SCOPES.get(collection)
    if not expected_scope:
        raise MemoryError("vector_collection_not_supported")
    if scope_type and scope_type != expected_scope:
        raise MemoryError("vector_scope_mismatch")
    return expected_scope


def _refuse_secret(*, sensitivity: str, content: str) -> None:
    if sensitivity == "secret_forbidden":
        raise MemoryError("secret_forbidden")
    lowered = content.lower()
    secret_markers = ("password=", "api_key", "secret=", "private_key")
    if any(marker in lowered for marker in secret_markers):
        raise MemoryError("secret_forbidden")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _record_for_entry(*, job: VectorIndexJob, entry: MemoryEntry) -> VectorIndexRecord:
    scope_key = _scope_key(entry=entry)
    content_hash = sha256(
        "|".join(
            (
                entry.title,
                entry.content,
                entry.source_ref,
                entry.verified_at.isoformat(),
            )
        ).encode("utf-8")
    ).hexdigest()
    vector_id = "vec_" + sha256(
        "|".join(
            (
                job.collection,
                scope_key,
                entry.id,
                job.embedding_model,
                job.embedding_version,
            )
        ).encode("utf-8")
    ).hexdigest()[:32]
    return VectorIndexRecord(
        id=f"vir_{uuid4().hex}",
        tenant_id=entry.tenant_id,
        user_id=entry.user_id if entry.scope_type == MemoryScope.PRIVATE_USER else None,
        scope_type=entry.scope_type,
        scope_key=scope_key,
        source_table="memory_entries",
        source_id=entry.id,
        collection=job.collection,
        shadow_collection=job.shadow_collection,
        vector_id=vector_id,
        index_status="shadow_pending",
        content_hash=content_hash,
        embedding_model=job.embedding_model,
        embedding_version=job.embedding_version,
        trace_id=job.trace_id,
        created_at=_utc_now(),
        job_id=job.id,
    )


def _scope_key(*, entry: MemoryEntry) -> str:
    if entry.scope_type == MemoryScope.PRIVATE_USER:
        raw_key = f"{entry.tenant_id}:{entry.user_id}"
    elif entry.scope_type == MemoryScope.ORGANIZATION:
        raw_key = f"{entry.tenant_id}:organization"
    else:
        raw_key = "shared_clean"
    return "sk_" + sha256(raw_key.encode("utf-8")).hexdigest()[:32]
