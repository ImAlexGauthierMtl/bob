"""Agent Memory application use cases."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import os
from typing import Optional, Protocol
from uuid import uuid4

import httpx

from app.domain import (
    InternalContext,
    KnowledgeChunk,
    MemoryEntry,
    MemoryError,
    MemoryForbiddenError,
    MemoryJournalEntry,
    MemoryNotFoundError,
    MemoryScope,
    KnowledgeCollection,
    KnowledgeDatabase,
    KnowledgeIngestionRun,
    KnowledgeItem,
    KnowledgeProcedure,
    KnowledgeSource,
    VectorIndexJob,
    VectorIndexRecord,
    VectorRevalidationMatch,
)


VECTOR_COLLECTION_SCOPES = {
    "bob_private_memory_chunks_v1": MemoryScope.PRIVATE_USER,
    "bob_organization_knowledge_chunks_v1": MemoryScope.ORGANIZATION,
    "bob_shared_skill_chunks_v1": MemoryScope.SHARED_CLEAN,
    "support_procedure_chunks_v1": MemoryScope.ORGANIZATION,
    "zoho_ticket_chunks_v1": MemoryScope.ORGANIZATION,
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

    def list_knowledge_databases(self, *, tenant_id: str) -> list[KnowledgeDatabase]:
        ...

    def list_knowledge_collections(self, *, tenant_id: str) -> list[KnowledgeCollection]:
        ...

    def list_knowledge_sources(self, *, tenant_id: str) -> list[KnowledgeSource]:
        ...

    def get_knowledge_database(self, *, tenant_id: str, database_id: str) -> KnowledgeDatabase | None:
        ...

    def get_knowledge_collection(self, *, tenant_id: str, collection_id: str) -> KnowledgeCollection | None:
        ...

    def get_knowledge_source(self, *, tenant_id: str, source_id: str) -> KnowledgeSource | None:
        ...

    def get_knowledge_database_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> KnowledgeDatabase | None:
        ...

    def get_knowledge_collection_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> KnowledgeCollection | None:
        ...

    def get_knowledge_source_by_idempotency_key(
        self,
        *,
        tenant_id: str,
        user_id: str,
        idempotency_key: str,
    ) -> KnowledgeSource | None:
        ...

    def create_knowledge_database(self, *, database: KnowledgeDatabase) -> KnowledgeDatabase:
        ...

    def create_knowledge_collection(self, *, collection: KnowledgeCollection) -> KnowledgeCollection:
        ...

    def create_knowledge_source(self, *, source: KnowledgeSource) -> KnowledgeSource:
        ...

    def create_knowledge_ingestion_run(self, *, run: KnowledgeIngestionRun) -> KnowledgeIngestionRun:
        ...

    def update_knowledge_ingestion_run(self, *, run: KnowledgeIngestionRun) -> KnowledgeIngestionRun:
        ...

    def upsert_knowledge_item(self, *, item: KnowledgeItem) -> KnowledgeItem:
        ...

    def create_knowledge_chunks(self, *, chunks: list[KnowledgeChunk]) -> list[KnowledgeChunk]:
        ...

    def create_knowledge_procedure(self, *, procedure: KnowledgeProcedure) -> KnowledgeProcedure:
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

    async def list_knowledge(self, *, context: InternalContext) -> dict[str, object]:
        _require_knowledge_permission(context)
        return {
            "databases": self.repo.list_knowledge_databases(tenant_id=context.tenant_id),
            "collections": self.repo.list_knowledge_collections(tenant_id=context.tenant_id),
            "sources": self.repo.list_knowledge_sources(tenant_id=context.tenant_id),
            "ingestion_flow": [
                "pipedream_source_event",
                "normalize_ticket",
                "generate_candidate_procedure",
                "store_postgres_source_of_truth",
                "embed_chunks",
                "upsert_milvus_index",
                "human_approval_before_execution",
            ],
        }

    async def create_knowledge_database(
        self,
        *,
        context: InternalContext,
        name: str,
        display_name: str,
        description: str,
        milvus_database: str,
        embedding_provider: str,
        embedding_model: str,
        embedding_dimension: int,
        idempotency_key: str,
    ) -> KnowledgeDatabase:
        _require_knowledge_permission(context)
        existing = self.repo.get_knowledge_database_by_idempotency_key(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            idempotency_key=idempotency_key,
        )
        if existing:
            return existing
        database = KnowledgeDatabase(
            id=f"kdb_{uuid4().hex}",
            tenant_id=context.tenant_id,
            name=_slug(name),
            display_name=display_name.strip() or name.strip(),
            description=description.strip(),
            status="active",
            milvus_database=_slug(milvus_database or name),
            embedding_provider=embedding_provider.strip() or "fireworks",
            embedding_model=embedding_model.strip(),
            embedding_dimension=embedding_dimension,
            created_by=context.user_id,
            created_at=_utc_now(),
            idempotency_key=idempotency_key,
        )
        return self.repo.create_knowledge_database(database=database)

    async def create_knowledge_collection(
        self,
        *,
        context: InternalContext,
        database_id: str,
        name: str,
        display_name: str,
        theme: str,
        description: str,
        milvus_collection: str,
        scope_type: str,
        source_kind: str,
        idempotency_key: str,
    ) -> KnowledgeCollection:
        _require_knowledge_permission(context)
        existing = self.repo.get_knowledge_collection_by_idempotency_key(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            idempotency_key=idempotency_key,
        )
        if existing:
            return existing
        if not self.repo.get_knowledge_database(tenant_id=context.tenant_id, database_id=database_id):
            raise MemoryNotFoundError("knowledge_database_not_found")
        if scope_type not in {MemoryScope.ORGANIZATION, MemoryScope.SHARED_CLEAN}:
            raise MemoryError("knowledge_collection_scope_invalid")
        collection = KnowledgeCollection(
            id=f"kcol_{uuid4().hex}",
            tenant_id=context.tenant_id,
            database_id=database_id,
            name=_slug(name),
            display_name=display_name.strip() or name.strip(),
            theme=theme.strip() or "support",
            description=description.strip(),
            status="candidate",
            milvus_collection=_slug(milvus_collection or name),
            scope_type=scope_type,
            source_kind=source_kind.strip() or "zoho_desk",
            created_by=context.user_id,
            created_at=_utc_now(),
            idempotency_key=idempotency_key,
        )
        return self.repo.create_knowledge_collection(collection=collection)

    async def create_knowledge_source(
        self,
        *,
        context: InternalContext,
        collection_id: str,
        name: str,
        provider: str,
        source_type: str,
        pipedream_app: str,
        pipedream_source_id: str | None,
        sync_mode: str,
        ingestion_strategy: str,
        idempotency_key: str,
    ) -> KnowledgeSource:
        _require_knowledge_permission(context)
        existing = self.repo.get_knowledge_source_by_idempotency_key(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            idempotency_key=idempotency_key,
        )
        if existing:
            return existing
        if not self.repo.get_knowledge_collection(tenant_id=context.tenant_id, collection_id=collection_id):
            raise MemoryNotFoundError("knowledge_collection_not_found")
        source = KnowledgeSource(
            id=f"ksrc_{uuid4().hex}",
            tenant_id=context.tenant_id,
            collection_id=collection_id,
            name=name.strip(),
            provider=provider.strip() or "pipedream",
            source_type=source_type.strip() or "zoho_desk",
            status="connection_required" if not pipedream_source_id else "connected",
            pipedream_app=pipedream_app.strip() or "zoho_desk",
            pipedream_source_id=pipedream_source_id,
            sync_mode=sync_mode.strip() or "incremental",
            ingestion_strategy=ingestion_strategy.strip() or "tickets_to_candidate_procedures",
            created_by=context.user_id,
            created_at=_utc_now(),
            idempotency_key=idempotency_key,
        )
        return self.repo.create_knowledge_source(source=source)

    async def ingest_zoho_ticket(
        self,
        *,
        context: InternalContext,
        source_id: str,
        ticket: dict[str, object],
        trigger_type: str,
        external_event_id: str | None,
        dry_run: bool,
    ) -> dict[str, object]:
        _require_knowledge_permission(context)
        source = self.repo.get_knowledge_source(tenant_id=context.tenant_id, source_id=source_id)
        if not source:
            raise MemoryNotFoundError("knowledge_source_not_found")
        collection = self.repo.get_knowledge_collection(tenant_id=context.tenant_id, collection_id=source.collection_id)
        if not collection:
            raise MemoryNotFoundError("knowledge_collection_not_found")
        run = self.repo.create_knowledge_ingestion_run(
            run=KnowledgeIngestionRun(
                id=f"kir_{uuid4().hex}",
                tenant_id=context.tenant_id,
                source_id=source.id,
                trigger_type=trigger_type or "pipedream_source_event",
                external_event_id=external_event_id,
                status="running",
                raw_items_count=1,
                normalized_items_count=0,
                candidate_procedures_count=0,
                error_message=None,
                started_at=_utc_now(),
                completed_at=None,
                metadata_json={"dry_run": dry_run},
            )
        )
        try:
            title, body, metadata = _normalize_zoho_ticket(ticket)
            content_hash = sha256(body.encode("utf-8")).hexdigest()
            item = self.repo.upsert_knowledge_item(
                item=KnowledgeItem(
                    id=f"kitem_{uuid4().hex}",
                    tenant_id=context.tenant_id,
                    source_id=source.id,
                    run_id=run.id,
                    external_id=str(metadata["ticket_id"]),
                    item_type="zoho_ticket",
                    title=title,
                    body=body,
                    metadata_json=metadata,
                    content_hash=content_hash,
                    status="normalized",
                    created_at=_utc_now(),
                    updated_at=_utc_now(),
                )
            )
            procedure_markdown = await _generate_candidate_procedure(title=title, body=body)
            procedure = self.repo.create_knowledge_procedure(
                procedure=KnowledgeProcedure(
                    id=f"kproc_{uuid4().hex}",
                    tenant_id=context.tenant_id,
                    collection_id=collection.id,
                    source_item_id=item.id,
                    title=f"Procedure candidate - {title[:180]}",
                    intent_key=_slug(title)[:160] or "zoho_ticket_intent",
                    trigger_summary=title,
                    procedure_markdown=procedure_markdown,
                    tool_plan_json=[
                        {"step": "understand_customer_request", "requires_human_approval": False},
                        {"step": "propose_tool_actions", "requires_human_approval": True},
                        {"step": "execute_after_approval", "requires_human_approval": True},
                    ],
                    confidence=60,
                    status="candidate",
                    generated_by_model=os.environ.get("FIREWORKS_LEARNING_MODEL", "template-fallback"),
                    approved_by=None,
                    approved_at=None,
                    created_at=_utc_now(),
                    updated_at=_utc_now(),
                )
            )
            chunk_texts = _chunk_texts([body, procedure_markdown])
            embeddings = await _embed_texts(chunk_texts)
            now = _utc_now()
            chunks = [
                KnowledgeChunk(
                    id=f"kchunk_{uuid4().hex}",
                    tenant_id=context.tenant_id,
                    collection_id=collection.id,
                    item_id=item.id,
                    chunk_index=index,
                    content=chunk,
                    content_hash=sha256(chunk.encode("utf-8")).hexdigest(),
                    metadata_json={"source": "zoho_desk", "procedure_id": procedure.id},
                    vector_id=f"{item.id}:{index}",
                    embedding_model=os.environ.get("EMBEDDINGS_MODEL", "accounts/fireworks/models/qwen3-embedding-8b"),
                    embedding_dimension=len(embeddings[index]),
                    milvus_collection=collection.milvus_collection,
                    status="planned" if dry_run else "indexed",
                    created_at=now,
                    indexed_at=None if dry_run else now,
                )
                for index, chunk in enumerate(chunk_texts)
            ]
            stored_chunks = self.repo.create_knowledge_chunks(chunks=chunks)
            milvus_upserted = 0
            if not dry_run:
                milvus_upserted = _upsert_milvus_chunks(
                    collection_name=collection.milvus_collection,
                    chunks=stored_chunks,
                    embeddings=embeddings,
                )
            completed = replace(
                run,
                status="completed",
                normalized_items_count=1,
                candidate_procedures_count=1,
                completed_at=_utc_now(),
                metadata_json={**run.metadata_json, "milvus_upserted": milvus_upserted},
            )
            self.repo.update_knowledge_ingestion_run(run=completed)
            return {
                "run_id": completed.id,
                "status": completed.status,
                "item_id": item.id,
                "procedure_id": procedure.id,
                "chunks": len(stored_chunks),
                "milvus_upserted": milvus_upserted,
                "dry_run": dry_run,
                "fireworks_api_key_set": bool(os.environ.get("FIREWORKS_API_KEY", "").strip()),
                "fallback_mode": "deterministic_when_fireworks_unavailable",
            }
        except Exception as exc:
            failed = replace(run, status="failed", error_message=str(exc), completed_at=_utc_now())
            self.repo.update_knowledge_ingestion_run(run=failed)
            raise

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


def _normalize_zoho_ticket(ticket: dict[str, object]) -> tuple[str, str, dict[str, object]]:
    ticket_id = str(ticket.get("id") or ticket.get("ticket_id") or ticket.get("number") or uuid4().hex)
    raw_subject = str(ticket.get("subject") or ticket.get("title") or "").strip()
    subject = raw_subject or "Zoho Desk ticket"
    description = str(ticket.get("description") or ticket.get("content") or ticket.get("body") or "").strip()
    status = str(ticket.get("status") or "").strip()
    category = str(ticket.get("category") or ticket.get("classification") or "").strip()
    customer = str(ticket.get("contact") or ticket.get("customer") or "").strip()
    threads = ticket.get("threads") if isinstance(ticket.get("threads"), list) else []
    thread_text = "\n".join(str(item.get("content") or item.get("body") or item) for item in threads[:10])
    if not any((raw_subject, description, status, category, customer, thread_text)):
        raise MemoryError("zoho_ticket_empty")
    body = "\n\n".join(
        part
        for part in (
            f"Ticket: {ticket_id}",
            f"Subject: {subject}",
            f"Status: {status}" if status else "",
            f"Category: {category}" if category else "",
            f"Customer: {customer}" if customer else "",
            description,
            thread_text,
        )
        if part
    )
    return subject, body, {
        "ticket_id": ticket_id,
        "status": status,
        "category": category,
        "customer": customer,
    }


async def _generate_candidate_procedure(*, title: str, body: str) -> str:
    api_key = os.environ.get("FIREWORKS_API_KEY", "").strip()
    model = os.environ.get("FIREWORKS_LEARNING_MODEL", "accounts/fireworks/models/gpt-oss-120b")
    if not api_key:
        return _fallback_procedure(title=title, body=body)
    prompt = (
        "Transforme ce ticket Zoho Desk en procedure candidate pour un agent Bob Chat. "
        "La procedure doit identifier l'intention client, les verifications, les actions outils, "
        "les points demandant validation humaine, et la reponse client proposee.\n\n"
        f"Titre: {title}\n\nTicket:\n{body[:8000]}"
    )
    try:
        async with httpx.AsyncClient(timeout=float(os.environ.get("FIREWORKS_TIMEOUT_SECONDS", "60"))) as client:
            response = await client.post(
                os.environ.get("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1").rstrip("/")
                + "/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "Tu ecris des procedures de support operationnelles, courtes et actionnables."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": float(os.environ.get("FIREWORKS_TEMPERATURE", "0.1")),
                    "top_p": float(os.environ.get("FIREWORKS_TOP_P", "0.8")),
                },
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"].strip()
            return content or _fallback_procedure(title=title, body=body)
    except Exception:
        return _fallback_procedure(title=title, body=body)


def _fallback_procedure(*, title: str, body: str) -> str:
    return (
        f"# Procedure candidate: {title}\n\n"
        "## Intention detectee\n"
        f"Le client demande de l'aide sur: {title}.\n\n"
        "## Verification\n"
        "- Lire le ticket et confirmer le compte/client concerne.\n"
        "- Identifier les outils necessaires avant toute execution.\n"
        "- Expliquer dans le chat ce que Bob comprend et ce qu'il propose de faire.\n\n"
        "## Action proposee\n"
        "- Preparer le plan d'action dans les outils disponibles.\n"
        "- Demander validation humaine avant modification, envoi ou fermeture du ticket.\n\n"
        "## Source\n"
        f"{body[:1200]}"
    )


def _chunk_texts(texts: list[str], *, max_chars: int = 1800) -> list[str]:
    chunks: list[str] = []
    for text in texts:
        clean = text.strip()
        for start in range(0, len(clean), max_chars):
            chunk = clean[start : start + max_chars].strip()
            if chunk:
                chunks.append(chunk)
    return chunks or ["empty knowledge chunk"]


async def _embed_texts(texts: list[str]) -> list[list[float]]:
    api_key = os.environ.get("FIREWORKS_API_KEY", "").strip()
    model = os.environ.get("EMBEDDINGS_MODEL", "accounts/fireworks/models/qwen3-embedding-8b")
    dimension = int(os.environ.get("EMBEDDINGS_DIMENSION", "4096"))
    if not api_key:
        return [_deterministic_embedding(text, dimension=dimension) for text in texts]
    try:
        async with httpx.AsyncClient(timeout=float(os.environ.get("FIREWORKS_TIMEOUT_SECONDS", "60"))) as client:
            response = await client.post(
                os.environ.get("FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1").rstrip() + "/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "input": texts},
            )
            response.raise_for_status()
            payload = response.json()
            vectors = [item["embedding"] for item in payload["data"]]
            if any(len(vector) != dimension for vector in vectors):
                raise MemoryError("embedding_dimension_mismatch")
            return vectors
    except Exception:
        return [_deterministic_embedding(text, dimension=dimension) for text in texts]


def _deterministic_embedding(text: str, *, dimension: int) -> list[float]:
    digest = sha256(text.encode("utf-8")).digest()
    values = [((digest[index % len(digest)] / 255.0) * 2.0) - 1.0 for index in range(dimension)]
    norm = sum(value * value for value in values) ** 0.5 or 1.0
    return [value / norm for value in values]


def _upsert_milvus_chunks(
    *,
    collection_name: str,
    chunks: list[KnowledgeChunk],
    embeddings: list[list[float]],
) -> int:
    if os.environ.get("MILVUS_ENABLED", "").strip().lower() not in {"1", "true", "yes", "on"}:
        return 0
    try:
        from pymilvus import MilvusClient

        client = MilvusClient(
            uri=os.environ.get("MILVUS_URI", ""),
            token=os.environ.get("MILVUS_TOKEN") or None,
            db_name=os.environ.get("MILVUS_DB_NAME", "default"),
            timeout=float(os.environ.get("MILVUS_CONNECT_TIMEOUT_SECONDS", "10")),
        )
        client.upsert(
            collection_name=collection_name,
            data=[
                {
                    "vector_id": chunk.vector_id,
                    "embedding": embeddings[index],
                    "tenant_id": chunk.tenant_id,
                    "item_id": chunk.item_id,
                    "chunk_id": chunk.id,
                    "content_hash": chunk.content_hash,
                }
                for index, chunk in enumerate(chunks)
            ],
        )
        return len(chunks)
    except Exception as exc:
        raise MemoryError("milvus_upsert_failed") from exc


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


def _require_knowledge_permission(context: InternalContext) -> None:
    if (
        "agent_memory.knowledge.manage" in context.permissions
        or "agent_memory.vector.manage" in context.permissions
        or "admin" in context.roles
    ):
        return
    raise MemoryForbiddenError("knowledge_forbidden")


def _slug(value: str) -> str:
    normalized = "".join(char.lower() if char.isalnum() else "_" for char in value.strip())
    collapsed = "_".join(part for part in normalized.split("_") if part)
    if not collapsed:
        raise MemoryError("knowledge_name_required")
    return collapsed[:120]


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
