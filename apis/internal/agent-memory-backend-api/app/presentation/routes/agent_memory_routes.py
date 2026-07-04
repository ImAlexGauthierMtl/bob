"""Internal Agent Memory routes."""

from __future__ import annotations

from hashlib import sha256

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.application.use_cases.agent_memory_use_cases import AgentMemoryUseCases
from app.domain import InternalContext, MemoryError, MemoryForbiddenError, MemoryNotFoundError
from app.presentation.deps import get_agent_memory_use_cases, get_internal_context
from app.presentation.schemas.agent_memory_schemas import (
    JournalRecordRequest,
    JournalResponse,
    KnowledgeCollectionRequest,
    KnowledgeCollectionResponse,
    KnowledgeDatabaseRequest,
    KnowledgeDatabaseResponse,
    KnowledgeOverviewResponse,
    KnowledgeSourceRequest,
    KnowledgeSourceResponse,
    MemoryEntryResponse,
    MemoryRecordRequest,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryStatusResponse,
    RagContextRequest,
    RagContextResponse,
    RagContextItemResponse,
    RagMilvusContextRequest,
    RagMilvusContextResponse,
    VectorCandidateResponse,
    VectorIndexJobResponse,
    VectorPrepareRequest,
    VectorPrepareResponse,
    VectorRebuildRequest,
    VectorRevalidateRequest,
    VectorRevalidateResponse,
    VectorRevalidationMatchResponse,
    VectorStoreHealthResponse,
    VectorStoreConfigResponse,
    VectorUpsertPlanRequest,
    VectorUpsertPlanResponse,
    ZohoDeskIngestionRequest,
    ZohoDeskIngestionResponse,
)
from app.infrastructure.vector import (
    EmbeddingConfig,
    EmbeddingConfigError,
    MilvusHealthCheck,
    MilvusConfig,
    MilvusConfigError,
    MilvusVectorSearch,
)


router = APIRouter(prefix="/internal/agent-memory/v1")


@router.get("/status", response_model=MemoryStatusResponse)
async def status_view(
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> MemoryStatusResponse:
    return MemoryStatusResponse(**await use_cases.status(context=context))


@router.post("/search", response_model=MemorySearchResponse)
async def search_private(
    body: MemorySearchRequest,
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> MemorySearchResponse:
    entries = await use_cases.search_private(
        context=context,
        query=body.query,
        memory_types=tuple(body.memory_types),
        limit=body.limit,
        include_sensitive=body.include_sensitive,
    )
    return MemorySearchResponse(
        results=[MemoryEntryResponse.from_domain(entry) for entry in entries],
        scope_type="private_user",
    )


@router.post("/organization/search", response_model=MemorySearchResponse)
async def search_organization(
    body: MemorySearchRequest,
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> MemorySearchResponse:
    try:
        entries = await use_cases.search_organization(
            context=context,
            query=body.query,
            memory_types=tuple(body.memory_types),
            limit=body.limit,
            include_sensitive=body.include_sensitive,
        )
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    return MemorySearchResponse(
        results=[MemoryEntryResponse.from_domain(entry) for entry in entries],
        scope_type="organization",
    )


@router.post("/entries", response_model=MemoryEntryResponse, status_code=status.HTTP_201_CREATED)
async def record_private_entry(
    body: MemoryRecordRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> MemoryEntryResponse:
    try:
        entry = await use_cases.record_private_entry(
            context=context,
            memory_type=body.memory_type,
            title=body.title,
            content=body.content,
            source_type=body.source_type,
            source_ref=body.source_ref,
            sensitivity=body.sensitivity,
            verified_at=body.verified_at,
            expires_at=body.expires_at,
            idempotency_key=idempotency_key,
        )
    except MemoryError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code}) from exc
    return MemoryEntryResponse.from_domain(entry)


@router.post(
    "/organization/entries",
    response_model=MemoryEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_organization_entry(
    body: MemoryRecordRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> MemoryEntryResponse:
    try:
        entry = await use_cases.record_organization_entry(
            context=context,
            memory_type=body.memory_type,
            title=body.title,
            content=body.content,
            source_type=body.source_type,
            source_ref=body.source_ref,
            sensitivity=body.sensitivity,
            verified_at=body.verified_at,
            expires_at=body.expires_at,
            idempotency_key=idempotency_key,
        )
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    except MemoryError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code}) from exc
    return MemoryEntryResponse.from_domain(entry)


@router.get("/entries/{entry_id}", response_model=MemoryEntryResponse)
async def get_entry(
    entry_id: str,
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> MemoryEntryResponse:
    try:
        entry = await use_cases.readback(context=context, entry_id=entry_id)
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    return MemoryEntryResponse.from_domain(entry)


@router.post("/entries/{entry_id}/readback", response_model=MemoryEntryResponse)
async def readback_entry(
    entry_id: str,
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> MemoryEntryResponse:
    return await get_entry(entry_id=entry_id, context=context, use_cases=use_cases)


@router.post("/journal", response_model=JournalResponse, status_code=status.HTTP_201_CREATED)
async def record_journal(
    body: JournalRecordRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> JournalResponse:
    try:
        entry = await use_cases.record_journal(
            context=context,
            request_summary=body.request_summary,
            actions_taken=body.actions_taken,
            sources_checked=body.sources_checked,
            result=body.result,
            next_step=body.next_step,
            sensitivity=body.sensitivity,
            idempotency_key=idempotency_key,
        )
    except MemoryError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code}) from exc
    return JournalResponse.from_domain(entry)


@router.post(
    "/vector-index/rebuild",
    response_model=VectorIndexJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_vector_rebuild_job(
    body: VectorRebuildRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> VectorIndexJobResponse:
    try:
        job = await use_cases.create_vector_rebuild_job(
            context=context,
            collection=body.collection,
            scope_type=body.scope_type,
            source_ref=body.source_ref,
            dry_run=body.dry_run,
            embedding_model=body.embedding_model,
            embedding_version=body.embedding_version,
            idempotency_key=idempotency_key,
        )
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    except MemoryError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code}) from exc
    return VectorIndexJobResponse.from_domain(job)


@router.get("/vector-index/jobs/{job_id}", response_model=VectorIndexJobResponse)
async def get_vector_job(
    job_id: str,
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> VectorIndexJobResponse:
    try:
        job = await use_cases.get_vector_job(context=context, job_id=job_id)
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    return VectorIndexJobResponse.from_domain(job)


@router.get("/vector-index/config", response_model=VectorStoreConfigResponse)
async def get_vector_config(
    context: InternalContext = Depends(get_internal_context),
) -> VectorStoreConfigResponse:
    if "agent_memory.vector.manage" not in context.permissions and "admin" not in context.roles:
        raise HTTPException(status_code=403, detail={"code": "vector_index_forbidden"})
    try:
        config = MilvusConfig.from_env()
        embedding_config = EmbeddingConfig.from_env()
    except MilvusConfigError as exc:
        raise HTTPException(status_code=503, detail={"code": exc.args[0]}) from exc
    except EmbeddingConfigError as exc:
        raise HTTPException(status_code=503, detail={"code": exc.args[0]}) from exc
    return VectorStoreConfigResponse(
        **config.redacted_status(),
        **embedding_config.redacted_status(),
    )


@router.get("/vector-index/health", response_model=VectorStoreHealthResponse)
async def get_vector_health(
    context: InternalContext = Depends(get_internal_context),
) -> VectorStoreHealthResponse:
    if "agent_memory.vector.manage" not in context.permissions and "admin" not in context.roles:
        raise HTTPException(status_code=403, detail={"code": "vector_index_forbidden"})
    try:
        config = MilvusConfig.from_env()
        embedding_config = EmbeddingConfig.from_env()
    except MilvusConfigError as exc:
        raise HTTPException(status_code=503, detail={"code": exc.args[0]}) from exc
    except EmbeddingConfigError as exc:
        raise HTTPException(status_code=503, detail={"code": exc.args[0]}) from exc
    health = MilvusHealthCheck().check(config=config)
    return VectorStoreHealthResponse(
        status=health.status,
        ready=health.ready and embedding_config.configured,
        checked=health.checked,
        enabled=config.enabled,
        configured=bool(config.uri),
        embedding_configured=embedding_config.configured,
        failure_code=health.failure_code,
    )


@router.get("/knowledge", response_model=KnowledgeOverviewResponse)
async def get_knowledge_overview(
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> KnowledgeOverviewResponse:
    try:
        payload = await use_cases.list_knowledge(context=context)
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    return KnowledgeOverviewResponse(
        databases=[
            KnowledgeDatabaseResponse.from_domain(database)
            for database in payload["databases"]
        ],
        collections=[
            KnowledgeCollectionResponse.from_domain(collection)
            for collection in payload["collections"]
        ],
        sources=[KnowledgeSourceResponse.from_domain(source) for source in payload["sources"]],
        ingestion_flow=list(payload["ingestion_flow"]),
    )


@router.post("/knowledge/databases", response_model=KnowledgeDatabaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_database(
    body: KnowledgeDatabaseRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> KnowledgeDatabaseResponse:
    try:
        database = await use_cases.create_knowledge_database(
            context=context,
            name=body.name,
            display_name=body.display_name,
            description=body.description,
            milvus_database=body.milvus_database,
            embedding_provider=body.embedding_provider,
            embedding_model=body.embedding_model,
            embedding_dimension=body.embedding_dimension,
            idempotency_key=idempotency_key,
        )
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    except MemoryError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code}) from exc
    return KnowledgeDatabaseResponse.from_domain(database)


@router.post("/knowledge/collections", response_model=KnowledgeCollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_collection(
    body: KnowledgeCollectionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> KnowledgeCollectionResponse:
    try:
        collection = await use_cases.create_knowledge_collection(
            context=context,
            database_id=body.database_id,
            name=body.name,
            display_name=body.display_name,
            theme=body.theme,
            description=body.description,
            milvus_collection=body.milvus_collection,
            scope_type=body.scope_type,
            source_kind=body.source_kind,
            idempotency_key=idempotency_key,
        )
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    except MemoryError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code}) from exc
    return KnowledgeCollectionResponse.from_domain(collection)


@router.post("/knowledge/sources", response_model=KnowledgeSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_source(
    body: KnowledgeSourceRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> KnowledgeSourceResponse:
    try:
        source = await use_cases.create_knowledge_source(
            context=context,
            collection_id=body.collection_id,
            name=body.name,
            provider=body.provider,
            source_type=body.source_type,
            pipedream_app=body.pipedream_app,
            pipedream_source_id=body.pipedream_source_id,
            sync_mode=body.sync_mode,
            ingestion_strategy=body.ingestion_strategy,
            idempotency_key=idempotency_key,
        )
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    except MemoryError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code}) from exc
    return KnowledgeSourceResponse.from_domain(source)


@router.post(
    "/knowledge/ingest/zoho-desk",
    response_model=ZohoDeskIngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_zoho_desk_ticket(
    body: ZohoDeskIngestionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> ZohoDeskIngestionResponse:
    _ = idempotency_key
    try:
        result = await use_cases.ingest_zoho_ticket(
            context=context,
            source_id=body.source_id,
            ticket=body.ticket,
            trigger_type=body.trigger_type,
            external_event_id=body.external_event_id,
            dry_run=body.dry_run,
        )
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    except MemoryError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code}) from exc
    return ZohoDeskIngestionResponse(**result)


@router.post(
    "/vector-index/jobs/{job_id}/prepare",
    response_model=VectorPrepareResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def prepare_vector_job(
    job_id: str,
    body: VectorPrepareRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> VectorPrepareResponse:
    _ = idempotency_key
    try:
        job, records = await use_cases.prepare_vector_job(
            context=context,
            job_id=job_id,
            limit=body.limit,
        )
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    return VectorPrepareResponse(
        job=VectorIndexJobResponse.from_domain(job),
        planned_records=len(records),
        stored_records=0 if job.dry_run else len(records),
    )


@router.post(
    "/vector-index/jobs/{job_id}/upsert-plan",
    response_model=VectorUpsertPlanResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def plan_vector_upsert(
    job_id: str,
    body: VectorUpsertPlanRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> VectorUpsertPlanResponse:
    _ = idempotency_key
    try:
        job, records = await use_cases.plan_vector_upsert(
            context=context,
            job_id=job_id,
            limit=body.limit,
        )
        config = MilvusConfig.from_env()
        embedding_config = EmbeddingConfig.from_env()
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    except MilvusConfigError as exc:
        raise HTTPException(status_code=503, detail={"code": exc.args[0]}) from exc
    except EmbeddingConfigError as exc:
        raise HTTPException(status_code=503, detail={"code": exc.args[0]}) from exc
    ready = bool(
        records
        and config.enabled
        and config.uri
        and embedding_config.configured
        and job.status in {"running", "queued"}
    )
    return VectorUpsertPlanResponse(
        job=VectorIndexJobResponse.from_domain(job),
        planned_records=len(records),
        milvus_enabled=config.enabled,
        milvus_configured=bool(config.uri),
        embedding_provider=embedding_config.provider,
        embedding_model_configured=bool(embedding_config.model),
        embedding_dimension=embedding_config.dimension,
        embedding_configured=embedding_config.configured,
        ready_for_upsert=ready,
    )


@router.post("/vector-index/revalidate", response_model=VectorRevalidateResponse)
async def revalidate_vector_results(
    body: VectorRevalidateRequest,
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> VectorRevalidateResponse:
    # Read-only POST: payload can exceed query limits, no Idempotency-Key required.
    try:
        matches = await use_cases.revalidate_vector_results(
            context=context,
            collection=body.collection,
            vector_ids=tuple(body.vector_ids),
        )
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    except MemoryError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code}) from exc
    accepted = len([match for match in matches if match.accepted])
    return VectorRevalidateResponse(
        collection=body.collection,
        requested=len(body.vector_ids),
        accepted=accepted,
        rejected=len(matches) - accepted,
        matches=[VectorRevalidationMatchResponse.from_domain(match) for match in matches],
    )


@router.post("/rag/context", response_model=RagContextResponse)
async def build_rag_context(
    body: RagContextRequest,
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> RagContextResponse:
    # Read-only POST: candidate vector IDs come from future ANN search output.
    try:
        matches, entries = await use_cases.build_rag_context_from_vectors(
            context=context,
            collection=body.collection,
            vector_ids=tuple(body.vector_ids),
            limit=body.limit,
        )
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    except MemoryError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code}) from exc
    accepted = len([match for match in matches if match.accepted])
    return RagContextResponse(
        collection=body.collection,
        trace_id=context.trace_id,
        audit_ref=_rag_audit_ref(
            trace_id=context.trace_id,
            collection=body.collection,
            vector_ids=tuple(body.vector_ids),
        ),
        requested=len(body.vector_ids),
        accepted=accepted,
        rejected=len(matches) - accepted,
        items=[RagContextItemResponse.from_domain(entry) for entry in entries],
        matches=[VectorRevalidationMatchResponse.from_domain(match) for match in matches],
    )


@router.post("/rag/milvus-context", response_model=RagMilvusContextResponse)
async def build_rag_context_from_milvus(
    body: RagMilvusContextRequest,
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> RagMilvusContextResponse:
    # Milvus provides ranking only; Postgres still revalidates before content.
    try:
        use_cases.authorize_rag_context(context=context)
        config = MilvusConfig.from_env()
        candidates = MilvusVectorSearch().search_candidates(
            config=config,
            collection=body.collection,
            query_vector=body.query_vector,
            limit=body.limit,
        )
        matches, entries = await use_cases.build_rag_context_from_vectors(
            context=context,
            collection=body.collection,
            vector_ids=tuple(candidate.vector_id for candidate in candidates),
            limit=body.limit,
        )
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    except MemoryError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code}) from exc
    except MilvusConfigError as exc:
        raise HTTPException(status_code=503, detail={"code": exc.args[0]}) from exc
    accepted = len([match for match in matches if match.accepted])
    return RagMilvusContextResponse(
        collection=body.collection,
        trace_id=context.trace_id,
        audit_ref=_rag_audit_ref(
            trace_id=context.trace_id,
            collection=body.collection,
            vector_ids=tuple(candidate.vector_id for candidate in candidates),
            query_hash=_query_vector_hash(body.query_vector),
        ),
        requested=len(candidates),
        accepted=accepted,
        rejected=len(matches) - accepted,
        items=[RagContextItemResponse.from_domain(entry) for entry in entries],
        matches=[VectorRevalidationMatchResponse.from_domain(match) for match in matches],
        candidates=[
            VectorCandidateResponse(
                vector_id=candidate.vector_id,
                rank=candidate.rank,
                distance=candidate.distance,
            )
            for candidate in candidates
        ],
    )


@router.post("/vector-index/jobs/{job_id}/rollback", response_model=VectorIndexJobResponse)
async def rollback_vector_job(
    job_id: str,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    context: InternalContext = Depends(get_internal_context),
    use_cases: AgentMemoryUseCases = Depends(get_agent_memory_use_cases),
) -> VectorIndexJobResponse:
    _ = idempotency_key
    try:
        job = await use_cases.rollback_vector_job(context=context, job_id=job_id)
    except MemoryForbiddenError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code}) from exc
    except MemoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code}) from exc
    return VectorIndexJobResponse.from_domain(job)


def _rag_audit_ref(
    *,
    trace_id: str,
    collection: str,
    vector_ids: tuple[str, ...],
    query_hash: str | None = None,
) -> str:
    raw = "|".join((trace_id, collection, query_hash or "", *vector_ids))
    return "ragctx_" + sha256(raw.encode("utf-8")).hexdigest()[:16]


def _query_vector_hash(query_vector: list[float]) -> str:
    normalized = ",".join(f"{value:.8g}" for value in query_vector)
    return sha256(normalized.encode("utf-8")).hexdigest()[:16]
