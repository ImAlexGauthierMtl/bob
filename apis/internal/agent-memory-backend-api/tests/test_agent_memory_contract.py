from dataclasses import replace
from datetime import datetime, timezone
import asyncio

from fastapi.testclient import TestClient
import pytest

import main
from app.application.use_cases.agent_memory_use_cases import AgentMemoryUseCases
from app.infrastructure.persistence.in_memory_agent_memory_repository import (
    InMemoryAgentMemoryRepository,
)
from app.infrastructure.vector import MilvusConfig, MilvusConfigError, MilvusHealthCheck
import app.infrastructure.vector.milvus_health as milvus_health
import app.infrastructure.vector.milvus_search as milvus_search
import app.application.use_cases.agent_memory_use_cases as agent_memory_use_cases
from app.presentation.routes import agent_memory_routes
from shared.infrastructure import InternalSessionContext, InternalSessionContextSigner


@pytest.fixture()
def memory_repo():
    return InMemoryAgentMemoryRepository()


@pytest.fixture()
def client(memory_repo):
    use_cases = AgentMemoryUseCases(repo=memory_repo)
    main.app.dependency_overrides[agent_memory_routes.get_agent_memory_use_cases] = lambda: use_cases
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


def signed_headers(
    *,
    tenant_id="tenant-croo-local",
    user_id="user-alex-local",
    permissions=("agent_memory.private.use",),
    roles=("support",),
):
    signer = InternalSessionContextSigner(
        "dev-internal-session-secret-not-for-production",
        kid="internal-session-dev",
    )
    context = InternalSessionContext(
        tenant_id=tenant_id,
        user_id=user_id,
        session_id="sess-bob-cloud-stub",
        trace_id="d" * 32,
        permissions=permissions,
        entitlements=permissions,
        roles=roles,
    )
    return {
        "X-Session-Context": signer.issue(context),
        "X-Trace-Id": "d" * 32,
    }


def memory_body(**overrides):
    body = {
        "memory_type": "preference",
        "title": "Style de reponse",
        "content": "Alexandre prefere une reponse courte et en francais.",
        "source_type": "chat",
        "source_ref": "thread-local-1",
        "sensitivity": "private_user",
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    body.update(overrides)
    return body


def test_monitoring_endpoints_do_not_require_internal_context(client):
    for path in ["/health", "/readiness", "/liveness", "/startup", "/metrics"]:
        response = client.get(path)
        assert response.status_code == 200


def test_internal_routes_require_signed_context(client):
    response = client.get("/internal/agent-memory/v1/status")

    assert response.status_code == 401


def test_record_private_memory_search_and_readback(client):
    created = client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(),
        headers={**signed_headers(), "Idempotency-Key": "private-1"},
    )
    replay = client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(title="Ignored replay"),
        headers={**signed_headers(), "Idempotency-Key": "private-1"},
    )
    search = client.post(
        "/internal/agent-memory/v1/search",
        json={"query": "francais", "memory_types": ["preference"]},
        headers=signed_headers(),
    )
    readback = client.post(
        f"/internal/agent-memory/v1/entries/{created.json()['id']}/readback",
        headers=signed_headers(),
    )

    assert created.status_code == 201
    assert replay.status_code == 201
    assert replay.json() == created.json()
    assert search.status_code == 200
    assert search.json()["scope_type"] == "private_user"
    assert search.json()["isolation_enforced"] is True
    assert search.json()["results"][0]["id"] == created.json()["id"]
    assert readback.status_code == 200
    assert readback.json()["id"] == created.json()["id"]


def test_private_memory_is_user_and_tenant_scoped(client):
    created = client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(),
        headers={**signed_headers(user_id="user-a"), "Idempotency-Key": "scope-1"},
    )
    entry_id = created.json()["id"]

    foreign_user_search = client.post(
        "/internal/agent-memory/v1/search",
        json={"query": "francais"},
        headers=signed_headers(user_id="user-b"),
    )
    foreign_user_readback = client.get(
        f"/internal/agent-memory/v1/entries/{entry_id}",
        headers=signed_headers(user_id="user-b"),
    )
    foreign_tenant_readback = client.get(
        f"/internal/agent-memory/v1/entries/{entry_id}",
        headers=signed_headers(tenant_id="tenant-other", user_id="user-a"),
    )

    assert foreign_user_search.status_code == 200
    assert foreign_user_search.json()["results"] == []
    assert foreign_user_readback.status_code == 404
    assert foreign_tenant_readback.status_code == 404


def test_secret_memory_is_refused(client):
    response = client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(content="password=super-secret", sensitivity="secret_forbidden"),
        headers={**signed_headers(), "Idempotency-Key": "secret-1"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == {"code": "secret_forbidden"}


def test_organization_memory_requires_permission_and_is_tenant_scoped(client):
    no_permission = client.post(
        "/internal/agent-memory/v1/organization/entries",
        json=memory_body(memory_type="organization_knowledge", sensitivity="internal"),
        headers={**signed_headers(), "Idempotency-Key": "org-1"},
    )
    created = client.post(
        "/internal/agent-memory/v1/organization/entries",
        json=memory_body(
            memory_type="organization_knowledge",
            title="Procedure support",
            content="Les procedures support Croo sont partagees par organisation.",
            sensitivity="internal",
        ),
        headers={
            **signed_headers(permissions=("agent_memory.organization.write",)),
            "Idempotency-Key": "org-1",
        },
    )
    search_same_tenant = client.post(
        "/internal/agent-memory/v1/organization/search",
        json={"query": "support"},
        headers=signed_headers(
            user_id="user-b",
            permissions=("agent_memory.organization.search",),
        ),
    )
    search_other_tenant = client.post(
        "/internal/agent-memory/v1/organization/search",
        json={"query": "support"},
        headers=signed_headers(
            tenant_id="tenant-other",
            user_id="user-b",
            permissions=("agent_memory.organization.search",),
        ),
    )

    assert no_permission.status_code == 403
    assert created.status_code == 201
    assert created.json()["scope_type"] == "organization"
    assert search_same_tenant.status_code == 200
    assert search_same_tenant.json()["results"][0]["id"] == created.json()["id"]
    assert search_other_tenant.status_code == 200
    assert search_other_tenant.json()["results"] == []


def test_status_counts_private_organization_and_journal(client):
    client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(),
        headers={**signed_headers(), "Idempotency-Key": "status-private"},
    )
    client.post(
        "/internal/agent-memory/v1/organization/entries",
        json=memory_body(memory_type="organization_knowledge", sensitivity="internal"),
        headers={
            **signed_headers(permissions=("agent_memory.organization.write",)),
            "Idempotency-Key": "status-org",
        },
    )
    journal = client.post(
        "/internal/agent-memory/v1/journal",
        json={
            "request_summary": "Test journal",
            "actions_taken": "Routes memoire validees",
            "sources_checked": "Contrat memoire privee",
            "result": "OK",
            "next_step": "Certification",
            "sensitivity": "internal",
        },
        headers={**signed_headers(), "Idempotency-Key": "journal-1"},
    )
    status_response = client.get(
        "/internal/agent-memory/v1/status",
        headers=signed_headers(),
    )

    assert journal.status_code == 201
    assert status_response.status_code == 200
    assert status_response.json()["memory_entries"] == 1
    assert status_response.json()["organization_entries"] == 1
    assert status_response.json()["journal_entries"] == 1
    assert status_response.json()["isolation_enforced"] is True


def test_vector_rebuild_job_requires_permission(client):
    response = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1"},
        headers={**signed_headers(), "Idempotency-Key": "vector-denied"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == {"code": "vector_index_forbidden"}


def test_vector_config_is_permissioned_and_redacted(client, monkeypatch):
    monkeypatch.setenv("MILVUS_ENABLED", "false")
    monkeypatch.setenv("MILVUS_URI", "http://milvus.example.invalid:19530")
    monkeypatch.setenv("MILVUS_TOKEN", "placeholder-redaction-token")
    forbidden = client.get(
        "/internal/agent-memory/v1/vector-index/config",
        headers=signed_headers(),
    )
    allowed = client.get(
        "/internal/agent-memory/v1/vector-index/config",
        headers=signed_headers(permissions=("agent_memory.vector.manage",)),
    )

    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["provider"] == "milvus"
    assert allowed.json()["enabled"] is False
    assert allowed.json()["configured"] is True
    assert allowed.json()["uri_configured"] is True
    assert allowed.json()["token_configured"] is True
    assert "milvus.example.invalid" not in str(allowed.json())
    assert "placeholder-redaction-token" not in str(allowed.json())
    assert allowed.json()["embedding_provider"] == "disabled"
    assert allowed.json()["embedding_configured"] is False


def test_vector_config_rejects_enabled_milvus_without_uri(client, monkeypatch):
    monkeypatch.setenv("MILVUS_ENABLED", "true")
    monkeypatch.delenv("MILVUS_URI", raising=False)
    response = client.get(
        "/internal/agent-memory/v1/vector-index/config",
        headers=signed_headers(permissions=("agent_memory.vector.manage",)),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == {"code": "milvus_uri_required"}


def test_knowledge_registry_lifecycle_is_permissioned_and_idempotent(client):
    forbidden = client.get("/internal/agent-memory/v1/knowledge", headers=signed_headers())
    headers = {
        **signed_headers(permissions=("agent_memory.knowledge.manage",)),
        "Idempotency-Key": "knowledge-db-1",
    }
    database = client.post(
        "/internal/agent-memory/v1/knowledge/databases",
        json={
            "name": "Bob Support Knowledge",
            "display_name": "Bob Support Knowledge",
            "description": "Zoho Desk support corpus",
            "milvus_database": "bob_knowledge",
            "embedding_provider": "fireworks",
            "embedding_model": "fireworks/qwen3-embedding-8b",
            "embedding_dimension": 4096,
        },
        headers=headers,
    )
    replay = client.post(
        "/internal/agent-memory/v1/knowledge/databases",
        json={
            "name": "Ignored",
            "display_name": "Ignored",
            "embedding_model": "ignored",
        },
        headers=headers,
    )
    collection = client.post(
        "/internal/agent-memory/v1/knowledge/collections",
        json={
            "database_id": database.json()["id"],
            "name": "Zoho Support Procedures",
            "display_name": "Zoho Support Procedures",
            "theme": "support_technique",
            "milvus_collection": "support_procedure_chunks_v1",
        },
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "knowledge-col-1",
        },
    )
    source = client.post(
        "/internal/agent-memory/v1/knowledge/sources",
        json={
            "collection_id": collection.json()["id"],
            "name": "Zoho Desk",
            "pipedream_app": "zoho_desk",
        },
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "knowledge-source-1",
        },
    )
    overview = client.get(
        "/internal/agent-memory/v1/knowledge",
        headers=signed_headers(permissions=("agent_memory.knowledge.manage",)),
    )

    assert forbidden.status_code == 403
    assert database.status_code == 201
    assert database.json()["name"] == "bob_support_knowledge"
    assert replay.json() == database.json()
    assert collection.status_code == 201
    assert collection.json()["status"] == "candidate"
    assert source.status_code == 201
    assert source.json()["status"] == "connection_required"
    assert overview.status_code == 200
    assert overview.json()["postgres_source_of_truth"] is True
    assert overview.json()["milvus_role"] == "reconstructible_vector_index"
    assert overview.json()["databases"][0]["id"] == database.json()["id"]


def test_knowledge_registry_rejects_orphan_collection_and_source(client):
    headers = {
        **signed_headers(permissions=("agent_memory.knowledge.manage",)),
        "Idempotency-Key": "knowledge-orphan-col",
    }
    collection = client.post(
        "/internal/agent-memory/v1/knowledge/collections",
        json={
            "database_id": "kdb_missing",
            "name": "Orphan",
            "display_name": "Orphan",
            "milvus_collection": "orphan_chunks_v1",
        },
        headers=headers,
    )
    source = client.post(
        "/internal/agent-memory/v1/knowledge/sources",
        json={
            "collection_id": "kcol_missing",
            "name": "Orphan source",
        },
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "knowledge-orphan-source",
        },
    )

    assert collection.status_code == 404
    assert collection.json()["detail"] == {"code": "knowledge_database_not_found"}
    assert source.status_code == 404
    assert source.json()["detail"] == {"code": "knowledge_collection_not_found"}


def test_knowledge_zoho_ingestion_creates_learning_records(client, memory_repo, monkeypatch):
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    database = client.post(
        "/internal/agent-memory/v1/knowledge/databases",
        json={
            "name": "Bob Support Knowledge",
            "display_name": "Bob Support Knowledge",
            "embedding_model": "accounts/fireworks/models/qwen3-embedding-8b",
            "embedding_dimension": 4096,
        },
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "ingest-db",
        },
    )
    collection = client.post(
        "/internal/agent-memory/v1/knowledge/collections",
        json={
            "database_id": database.json()["id"],
            "name": "Zoho Ticket History",
            "display_name": "Zoho Ticket History",
            "milvus_collection": "zoho_ticket_chunks_v1",
        },
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "ingest-col",
        },
    )
    source = client.post(
        "/internal/agent-memory/v1/knowledge/sources",
        json={"collection_id": collection.json()["id"], "name": "Zoho Desk"},
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "ingest-source",
        },
    )

    response = client.post(
        "/internal/agent-memory/v1/knowledge/ingest/zoho-desk",
        json={
            "source_id": source.json()["id"],
            "dry_run": True,
            "external_event_id": "evt-zoho-1",
            "ticket": {
                "id": "71638",
                "subject": "Le client demande X",
                "description": "Le client demande X; l'agent doit faire Y apres validation.",
            },
        },
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "ingest-run",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "completed"
    assert response.json()["chunks"] >= 1
    assert response.json()["milvus_upserted"] == 0
    assert response.json()["dry_run"] is True
    assert response.json()["fallback_mode"] == "deterministic_when_fireworks_unavailable"
    assert len(memory_repo.knowledge_ingestion_runs) == 1
    assert len(memory_repo.knowledge_items) == 1
    assert len(memory_repo.knowledge_chunks) == response.json()["chunks"]
    assert len(memory_repo.knowledge_procedures) == 1


def test_knowledge_zoho_ingestion_upserts_milvus_when_enabled(client, monkeypatch):
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    upserted = {}

    def fake_upsert(*, collection_name, chunks, embeddings):
        upserted["collection_name"] = collection_name
        upserted["chunks"] = len(chunks)
        upserted["dimensions"] = {len(vector) for vector in embeddings}
        return len(chunks)

    monkeypatch.setattr(agent_memory_use_cases, "_upsert_milvus_chunks", fake_upsert)
    database = client.post(
        "/internal/agent-memory/v1/knowledge/databases",
        json={"name": "Bob Support", "display_name": "Bob Support"},
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "ingest-upsert-db",
        },
    )
    collection = client.post(
        "/internal/agent-memory/v1/knowledge/collections",
        json={
            "database_id": database.json()["id"],
            "name": "Zoho Ticket History",
            "display_name": "Zoho Ticket History",
            "milvus_collection": "zoho_ticket_chunks_v1",
        },
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "ingest-upsert-col",
        },
    )
    source = client.post(
        "/internal/agent-memory/v1/knowledge/sources",
        json={"collection_id": collection.json()["id"], "name": "Zoho Desk"},
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "ingest-upsert-source",
        },
    )

    response = client.post(
        "/internal/agent-memory/v1/knowledge/ingest/zoho-desk",
        json={
            "source_id": source.json()["id"],
            "ticket": {"id": "71690", "subject": "Connexion Zoho", "description": "Procedure de connexion."},
        },
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "ingest-upsert-run",
        },
    )
    missing = client.post(
        "/internal/agent-memory/v1/knowledge/ingest/zoho-desk",
        json={"source_id": "ksrc_missing", "ticket": {"id": "1", "subject": "Missing"}},
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "ingest-missing-source",
        },
    )

    assert response.status_code == 202
    assert response.json()["milvus_upserted"] == upserted["chunks"]
    assert response.json()["fireworks_api_key_set"] is False
    assert upserted["collection_name"] == "zoho_ticket_chunks_v1"
    assert upserted["dimensions"] == {4096}
    assert missing.status_code == 404
    assert missing.json()["detail"] == {"code": "knowledge_source_not_found"}


def test_knowledge_ingestion_helpers_cover_fireworks_fallbacks(monkeypatch):
    title, body, metadata = agent_memory_use_cases._normalize_zoho_ticket(
        {
            "id": "71638",
            "subject": "Connexion impossible",
            "status": "Open",
            "category": "Login",
            "threads": [{"content": "Le client ne peut pas se connecter."}],
        }
    )
    chunks = agent_memory_use_cases._chunk_texts([body, "Procedure"], max_chars=20)
    vector = agent_memory_use_cases._deterministic_embedding("abc", dimension=8)
    monkeypatch.setenv("FIREWORKS_API_KEY", "invalid")
    monkeypatch.setenv("FIREWORKS_BASE_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("FIREWORKS_TIMEOUT_SECONDS", "0.01")
    procedure = asyncio.run(agent_memory_use_cases._generate_candidate_procedure(title=title, body=body))
    embeddings = asyncio.run(agent_memory_use_cases._embed_texts(["abc", "def"]))
    monkeypatch.setenv("MILVUS_ENABLED", "false")
    skipped = agent_memory_use_cases._upsert_milvus_chunks(
        collection_name="zoho_ticket_chunks_v1",
        chunks=[],
        embeddings=[],
    )

    assert title == "Connexion impossible"
    assert metadata["ticket_id"] == "71638"
    assert len(chunks) >= 2
    assert len(vector) == 8
    assert "Procedure candidate" in procedure
    assert len(embeddings) == 2
    assert {len(item) for item in embeddings} == {4096}
    assert skipped == 0


def test_knowledge_zoho_ingestion_rejects_forbidden_and_empty_ticket(client):
    forbidden = client.post(
        "/internal/agent-memory/v1/knowledge/ingest/zoho-desk",
        json={"source_id": "ksrc_missing", "ticket": {"id": "1", "subject": "No permission"}},
        headers={**signed_headers(), "Idempotency-Key": "ingest-forbidden"},
    )
    database = client.post(
        "/internal/agent-memory/v1/knowledge/databases",
        json={"name": "Bob Support", "display_name": "Bob Support"},
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "ingest-empty-db",
        },
    )
    collection = client.post(
        "/internal/agent-memory/v1/knowledge/collections",
        json={
            "database_id": database.json()["id"],
            "name": "Zoho",
            "display_name": "Zoho",
            "milvus_collection": "zoho_ticket_chunks_v1",
        },
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "ingest-empty-col",
        },
    )
    source = client.post(
        "/internal/agent-memory/v1/knowledge/sources",
        json={"collection_id": collection.json()["id"], "name": "Zoho Desk"},
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "ingest-empty-source",
        },
    )
    empty = client.post(
        "/internal/agent-memory/v1/knowledge/ingest/zoho-desk",
        json={"source_id": source.json()["id"], "ticket": {}},
        headers={
            **signed_headers(permissions=("agent_memory.knowledge.manage",)),
            "Idempotency-Key": "ingest-empty-run",
        },
    )

    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == {"code": "knowledge_forbidden"}
    assert empty.status_code == 400
    assert empty.json()["detail"] == {"code": "zoho_ticket_empty"}


def test_vector_config_rejects_invalid_embedding_dimension(client, monkeypatch):
    monkeypatch.setenv("EMBEDDINGS_DIMENSION", "0")
    response = client.get(
        "/internal/agent-memory/v1/vector-index/config",
        headers=signed_headers(permissions=("agent_memory.vector.manage",)),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == {"code": "embeddings_dimension_invalid"}


def test_vector_health_is_permissioned_redacted_and_skips_disabled_milvus(client, monkeypatch):
    monkeypatch.setenv("MILVUS_ENABLED", "false")
    monkeypatch.setenv("MILVUS_URI", "http://milvus.example.invalid:19530")
    monkeypatch.setenv("MILVUS_TOKEN", "placeholder-redaction-token")

    forbidden = client.get(
        "/internal/agent-memory/v1/vector-index/health",
        headers=signed_headers(),
    )
    allowed = client.get(
        "/internal/agent-memory/v1/vector-index/health",
        headers=signed_headers(permissions=("agent_memory.vector.manage",)),
    )

    assert forbidden.status_code == 403
    assert allowed.status_code == 200
    assert allowed.json()["provider"] == "milvus"
    assert allowed.json()["status"] == "disabled"
    assert allowed.json()["ready"] is False
    assert allowed.json()["checked"] is False
    assert allowed.json()["enabled"] is False
    assert allowed.json()["configured"] is True
    assert allowed.json()["embedding_configured"] is False
    assert "milvus.example.invalid" not in str(allowed.json())
    assert "placeholder-redaction-token" not in str(allowed.json())


def test_vector_health_reports_ready_when_milvus_and_embeddings_are_ready(client, monkeypatch):
    class ReadyHealthCheck:
        def check(self, *, config):
            assert config.uri == "http://milvus:19530"
            return type(
                "ReadyStatus",
                (),
                {
                    "status": "ready",
                    "ready": True,
                    "checked": True,
                    "failure_code": None,
                },
            )()

    monkeypatch.setattr(agent_memory_routes, "MilvusHealthCheck", ReadyHealthCheck)
    monkeypatch.setenv("MILVUS_ENABLED", "true")
    monkeypatch.setenv("MILVUS_URI", "http://milvus:19530")
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "openai-compatible")
    monkeypatch.setenv("EMBEDDINGS_MODEL", "text-embedding-test")

    response = client.get(
        "/internal/agent-memory/v1/vector-index/health",
        headers=signed_headers(permissions=("agent_memory.vector.manage",)),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["ready"] is True
    assert response.json()["checked"] is True
    assert response.json()["enabled"] is True
    assert response.json()["configured"] is True
    assert response.json()["embedding_configured"] is True
    assert response.json()["failure_code"] is None
    assert "http://milvus:19530" not in str(response.json())


def test_milvus_health_check_covers_disabled_and_misconfigured():
    disabled = MilvusHealthCheck().check(
        config=MilvusConfig(
            enabled=False,
            uri="",
            token="",
            database="default",
            secure=False,
            timeout_seconds=5,
            default_dimension=1536,
        )
    )
    missing_uri = MilvusHealthCheck().check(
        config=MilvusConfig(
            enabled=True,
            uri="",
            token="",
            database="default",
            secure=False,
            timeout_seconds=5,
            default_dimension=1536,
        )
    )

    assert disabled.status == "disabled"
    assert disabled.ready is False
    assert disabled.checked is False
    assert missing_uri.status == "misconfigured"
    assert missing_uri.failure_code == "milvus_uri_required"


def test_milvus_health_check_covers_ready_config_error_and_connection_error(monkeypatch):
    config = MilvusConfig(
        enabled=True,
        uri="http://milvus:19530",
        token="placeholder",
        database="default",
        secure=False,
        timeout_seconds=5,
        default_dimension=1536,
    )

    class ReadyClient:
        def list_collections(self):
            return ["bob_private_memory_chunks_v1"]

    class ReadyFactory:
        def __init__(self, *, config):
            self.config = config

        def create(self):
            return ReadyClient()

    monkeypatch.setattr(milvus_health, "MilvusClientFactory", ReadyFactory)
    ready = MilvusHealthCheck().check(config=config)

    class ConfigErrorFactory:
        def __init__(self, *, config):
            self.config = config

        def create(self):
            raise MilvusConfigError("pymilvus_not_installed")

    monkeypatch.setattr(milvus_health, "MilvusClientFactory", ConfigErrorFactory)
    config_error = MilvusHealthCheck().check(config=config)

    class UnknownConfigErrorFactory:
        def __init__(self, *, config):
            self.config = config

        def create(self):
            raise MilvusConfigError("free form provider detail")

    monkeypatch.setattr(milvus_health, "MilvusClientFactory", UnknownConfigErrorFactory)
    unknown_config_error = MilvusHealthCheck().check(config=config)

    class FailingClient:
        def list_collections(self):
            raise RuntimeError("boom")

    class ConnectionErrorFactory:
        def __init__(self, *, config):
            self.config = config

        def create(self):
            return FailingClient()

    monkeypatch.setattr(milvus_health, "MilvusClientFactory", ConnectionErrorFactory)
    connection_error = MilvusHealthCheck().check(config=config)

    assert ready.status == "ready"
    assert ready.ready is True
    assert ready.checked is True
    assert config_error.status == "unavailable"
    assert config_error.failure_code == "pymilvus_not_installed"
    assert unknown_config_error.status == "unavailable"
    assert unknown_config_error.failure_code == "milvus_config_failed"
    assert connection_error.status == "unavailable"
    assert connection_error.failure_code == "milvus_connection_failed"


def test_shared_health_reports_milvus_only_when_configured(monkeypatch):
    from shared.infrastructure.monitoring import _dependency_status

    monkeypatch.delenv("MILVUS_ENABLED", raising=False)
    monkeypatch.delenv("MILVUS_URI", raising=False)
    assert "milvus" not in _dependency_status()

    monkeypatch.setenv("MILVUS_ENABLED", "true")
    assert _dependency_status()["milvus"] == "not_configured"

    monkeypatch.setenv("MILVUS_URI", "http://milvus:19530")
    assert _dependency_status()["milvus"] == "configured"


def test_vector_rebuild_job_lifecycle(client):
    headers = {
        **signed_headers(permissions=("agent_memory.vector.manage",)),
        "Idempotency-Key": "vector-1",
    }
    created = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={
            "collection": "bob_private_memory_chunks_v1",
            "scope_type": "private_user",
            "source_ref": "mem_123",
            "dry_run": True,
            "embedding_model": "text-embedding-test",
            "embedding_version": "v1",
        },
        headers=headers,
    )
    replay = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1", "scope_type": "private_user"},
        headers=headers,
    )
    fetched = client.get(
        f"/internal/agent-memory/v1/vector-index/jobs/{created.json()['id']}",
        headers=signed_headers(permissions=("agent_memory.vector.manage",)),
    )
    rolled_back = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{created.json()['id']}/rollback",
        headers={
            **signed_headers(permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-rollback-1",
        },
    )

    assert created.status_code == 202
    assert created.json()["status"] == "queued"
    assert created.json()["shadow_collection"].startswith("bob_private_memory_chunks_v1__rebuild_vij_")
    assert created.json()["dry_run"] is True
    assert replay.json() == created.json()
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created.json()["id"]
    assert rolled_back.status_code == 200
    assert rolled_back.json()["status"] == "rolled_back"
    assert rolled_back.json()["rollback_of_job_id"] == created.json()["id"]


def test_vector_prepare_private_job_scopes_user_and_rolls_back_records(client, memory_repo):
    user_a = client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(title="Vector source A"),
        headers={**signed_headers(user_id="user-a"), "Idempotency-Key": "vector-source-a"},
    )
    client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(title="Vector source B"),
        headers={**signed_headers(user_id="user-b"), "Idempotency-Key": "vector-source-b"},
    )
    job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={
            "collection": "bob_private_memory_chunks_v1",
            "embedding_model": "text-embedding-test",
            "embedding_version": "v2",
        },
        headers={
            **signed_headers(user_id="user-a", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-prepare-job",
        },
    )
    prepared = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="user-a", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-prepare-1",
        },
    )
    replay = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="user-a", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-prepare-1-replay",
        },
    )

    records = list(memory_repo.vector_records.values())
    assert user_a.status_code == 201
    assert job.status_code == 202
    assert prepared.status_code == 202
    assert prepared.json()["planned_records"] == 1
    assert prepared.json()["stored_records"] == 1
    assert prepared.json()["job"]["status"] == "running"
    assert replay.json()["planned_records"] == 1
    assert len(records) == 1
    assert records[0].source_id == user_a.json()["id"]
    assert records[0].user_id == "user-a"
    assert records[0].scope_key.startswith("sk_")
    assert "tenant-croo-local" not in records[0].scope_key
    assert "user-a" not in records[0].scope_key
    assert records[0].shadow_collection == job.json()["shadow_collection"]
    assert records[0].index_status == "shadow_pending"

    rolled_back = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/rollback",
        headers={
            **signed_headers(user_id="user-a", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-prepare-rollback",
        },
    )

    assert rolled_back.status_code == 200
    assert memory_repo.vector_records[records[0].id].index_status == "rolled_back"


def test_vector_upsert_plan_reports_readiness_without_network(client, monkeypatch):
    client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(title="Upsert source"),
        headers={**signed_headers(user_id="user-upsert"), "Idempotency-Key": "vector-upsert-source"},
    )
    job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1"},
        headers={
            **signed_headers(user_id="user-upsert", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-upsert-job",
        },
    )
    client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="user-upsert", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-upsert-prepare",
        },
    )
    default_plan = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/upsert-plan",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="user-upsert", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-upsert-plan-default",
        },
    )
    monkeypatch.setenv("MILVUS_ENABLED", "true")
    monkeypatch.setenv("MILVUS_URI", "http://milvus:19530")
    monkeypatch.setenv("EMBEDDINGS_PROVIDER", "openai-compatible")
    monkeypatch.setenv("EMBEDDINGS_MODEL", "text-embedding-test")
    monkeypatch.setenv("EMBEDDINGS_DIMENSION", "1536")
    ready_plan = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/upsert-plan",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="user-upsert", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-upsert-plan-ready",
        },
    )

    assert default_plan.status_code == 202
    assert default_plan.json()["planned_records"] == 1
    assert default_plan.json()["milvus_enabled"] is False
    assert default_plan.json()["ready_for_upsert"] is False
    assert ready_plan.status_code == 202
    assert ready_plan.json()["planned_records"] == 1
    assert ready_plan.json()["milvus_enabled"] is True
    assert ready_plan.json()["milvus_configured"] is True
    assert ready_plan.json()["embedding_provider"] == "openai-compatible"
    assert ready_plan.json()["embedding_model_configured"] is True
    assert ready_plan.json()["embedding_configured"] is True
    assert ready_plan.json()["ready_for_upsert"] is True
    assert "http://milvus:19530" not in str(ready_plan.json())


def test_vector_upsert_plan_keeps_private_job_owner_scope(client):
    client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(title="Upsert owner source"),
        headers={**signed_headers(user_id="user-upsert-owner"), "Idempotency-Key": "vector-upsert-owner-source"},
    )
    job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1"},
        headers={
            **signed_headers(user_id="user-upsert-owner", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-upsert-owner-job",
        },
    )
    owner_plan_before_prepare = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/upsert-plan",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="user-upsert-owner", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-upsert-owner-plan-empty",
        },
    )
    foreign_plan = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/upsert-plan",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="user-upsert-foreign", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-upsert-foreign-plan",
        },
    )

    assert owner_plan_before_prepare.status_code == 202
    assert owner_plan_before_prepare.json()["planned_records"] == 0
    assert owner_plan_before_prepare.json()["ready_for_upsert"] is False
    assert foreign_plan.status_code == 404


def test_vector_upsert_plan_rejects_invalid_embedding_dimension(client, monkeypatch):
    job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1"},
        headers={
            **signed_headers(permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-upsert-invalid-embedding-job",
        },
    )
    monkeypatch.setenv("EMBEDDINGS_DIMENSION", "0")

    response = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/upsert-plan",
        json={"limit": 10},
        headers={
            **signed_headers(permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-upsert-invalid-embedding-plan",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == {"code": "embeddings_dimension_invalid"}


def test_vector_revalidate_filters_private_scope_missing_and_inactive_sources(client, memory_repo):
    owner_entry = client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(title="Owner indexed source"),
        headers={**signed_headers(user_id="user-owner"), "Idempotency-Key": "revalidate-owner-source"},
    )
    owner_job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1"},
        headers={
            **signed_headers(user_id="user-owner", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "revalidate-owner-job",
        },
    )
    client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{owner_job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="user-owner", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "revalidate-owner-prepare",
        },
    )
    memory_repo.update_vector_records_status_for_job(
        tenant_id="tenant-croo-local",
        job_id=owner_job.json()["id"],
        status="indexed",
    )
    owner_record = memory_repo.get_vector_records_for_job(
        tenant_id="tenant-croo-local",
        job_id=owner_job.json()["id"],
    )[0]

    client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(title="Foreign indexed source"),
        headers={**signed_headers(user_id="user-foreign"), "Idempotency-Key": "revalidate-foreign-source"},
    )
    foreign_job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1"},
        headers={
            **signed_headers(user_id="user-foreign", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "revalidate-foreign-job",
        },
    )
    client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{foreign_job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="user-foreign", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "revalidate-foreign-prepare",
        },
    )
    memory_repo.update_vector_records_status_for_job(
        tenant_id="tenant-croo-local",
        job_id=foreign_job.json()["id"],
        status="indexed",
    )
    foreign_record = memory_repo.get_vector_records_for_job(
        tenant_id="tenant-croo-local",
        job_id=foreign_job.json()["id"],
    )[0]

    client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(title="Other tenant indexed source"),
        headers={
            **signed_headers(tenant_id="tenant-other", user_id="user-owner"),
            "Idempotency-Key": "revalidate-other-tenant-source",
        },
    )
    other_tenant_job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1"},
        headers={
            **signed_headers(
                tenant_id="tenant-other",
                user_id="user-owner",
                permissions=("agent_memory.vector.manage",),
            ),
            "Idempotency-Key": "revalidate-other-tenant-job",
        },
    )
    client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{other_tenant_job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(
                tenant_id="tenant-other",
                user_id="user-owner",
                permissions=("agent_memory.vector.manage",),
            ),
            "Idempotency-Key": "revalidate-other-tenant-prepare",
        },
    )
    memory_repo.update_vector_records_status_for_job(
        tenant_id="tenant-other",
        job_id=other_tenant_job.json()["id"],
        status="indexed",
    )
    other_tenant_record = memory_repo.get_vector_records_for_job(
        tenant_id="tenant-other",
        job_id=other_tenant_job.json()["id"],
    )[0]

    mixed = client.post(
        "/internal/agent-memory/v1/vector-index/revalidate",
        json={
            "collection": "bob_private_memory_chunks_v1",
            "vector_ids": [
                owner_record.vector_id,
                foreign_record.vector_id,
                other_tenant_record.vector_id,
                "vec_missing",
            ],
        },
        headers=signed_headers(user_id="user-owner", permissions=("agent_memory.vector.manage",)),
    )
    memory_repo.entries[owner_entry.json()["id"]] = replace(
        memory_repo.entries[owner_entry.json()["id"]],
        status="tombstoned",
    )
    inactive = client.post(
        "/internal/agent-memory/v1/vector-index/revalidate",
        json={"collection": "bob_private_memory_chunks_v1", "vector_ids": [owner_record.vector_id]},
        headers=signed_headers(user_id="user-owner", permissions=("agent_memory.vector.manage",)),
    )

    assert mixed.status_code == 200
    assert mixed.json()["accepted"] == 1
    assert mixed.json()["rejected"] == 3
    assert mixed.json()["matches"][0]["accepted"] is True
    assert mixed.json()["matches"][0]["source_id"] == owner_entry.json()["id"]
    assert mixed.json()["matches"][1]["rejection_code"] == "private_scope_mismatch"
    assert mixed.json()["matches"][2]["rejection_code"] == "vector_record_not_found"
    assert mixed.json()["matches"][3]["rejection_code"] == "vector_record_not_found"
    assert "Owner indexed source" not in str(mixed.json())
    assert "Other tenant indexed source" not in str(mixed.json())
    assert "tenant-other" not in str(mixed.json())
    assert inactive.status_code == 200
    assert inactive.json()["accepted"] == 0
    assert inactive.json()["matches"][0]["rejection_code"] == "source_not_active"


def test_vector_revalidate_requires_organization_permission_for_org_vectors(client, memory_repo):
    client.post(
        "/internal/agent-memory/v1/organization/entries",
        json=memory_body(memory_type="organization_knowledge", sensitivity="internal"),
        headers={
            **signed_headers(permissions=("agent_memory.organization.write",)),
            "Idempotency-Key": "revalidate-org-source",
        },
    )
    org_job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_organization_knowledge_chunks_v1"},
        headers={
            **signed_headers(permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "revalidate-org-job",
        },
    )
    client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{org_job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "revalidate-org-prepare",
        },
    )
    memory_repo.update_vector_records_status_for_job(
        tenant_id="tenant-croo-local",
        job_id=org_job.json()["id"],
        status="indexed",
    )
    org_record = memory_repo.get_vector_records_for_job(
        tenant_id="tenant-croo-local",
        job_id=org_job.json()["id"],
    )[0]

    forbidden = client.post(
        "/internal/agent-memory/v1/vector-index/revalidate",
        json={
            "collection": "bob_organization_knowledge_chunks_v1",
            "vector_ids": [org_record.vector_id],
        },
        headers=signed_headers(permissions=("agent_memory.vector.manage",)),
    )
    allowed = client.post(
        "/internal/agent-memory/v1/vector-index/revalidate",
        json={
            "collection": "bob_organization_knowledge_chunks_v1",
            "vector_ids": [org_record.vector_id],
        },
        headers=signed_headers(
            permissions=("agent_memory.vector.manage", "agent_memory.organization.search"),
        ),
    )

    assert forbidden.status_code == 200
    assert forbidden.json()["accepted"] == 0
    assert forbidden.json()["matches"][0]["rejection_code"] == "organization_scope_forbidden"
    assert allowed.status_code == 200
    assert allowed.json()["accepted"] == 1
    assert allowed.json()["matches"][0]["accepted"] is True


def test_rag_context_returns_only_revalidated_private_memory(client, memory_repo):
    owner_entry = client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(
            title="RAG owner context",
            content="Le contexte RAG prive autorise peut nourrir Bob.",
        ),
        headers={**signed_headers(user_id="rag-owner"), "Idempotency-Key": "rag-owner-source"},
    )
    owner_job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1"},
        headers={
            **signed_headers(user_id="rag-owner", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "rag-owner-job",
        },
    )
    client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{owner_job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="rag-owner", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "rag-owner-prepare",
        },
    )
    memory_repo.update_vector_records_status_for_job(
        tenant_id="tenant-croo-local",
        job_id=owner_job.json()["id"],
        status="indexed",
    )
    owner_record = memory_repo.get_vector_records_for_job(
        tenant_id="tenant-croo-local",
        job_id=owner_job.json()["id"],
    )[0]

    client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(
            title="RAG foreign context",
            content="Ce contexte prive etranger ne doit jamais sortir.",
        ),
        headers={**signed_headers(user_id="rag-foreign"), "Idempotency-Key": "rag-foreign-source"},
    )
    foreign_job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1"},
        headers={
            **signed_headers(user_id="rag-foreign", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "rag-foreign-job",
        },
    )
    client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{foreign_job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="rag-foreign", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "rag-foreign-prepare",
        },
    )
    memory_repo.update_vector_records_status_for_job(
        tenant_id="tenant-croo-local",
        job_id=foreign_job.json()["id"],
        status="indexed",
    )
    foreign_record = memory_repo.get_vector_records_for_job(
        tenant_id="tenant-croo-local",
        job_id=foreign_job.json()["id"],
    )[0]

    sensitive_entry = client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(
            title="RAG sensitive context",
            content="Ce contexte sensible ne doit pas nourrir Bob.",
            sensitivity="new_sensitive_label",
        ),
        headers={**signed_headers(user_id="rag-owner"), "Idempotency-Key": "rag-sensitive-source"},
    )
    sensitive_job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={
            "collection": "bob_private_memory_chunks_v1",
            "source_ref": sensitive_entry.json()["id"],
        },
        headers={
            **signed_headers(user_id="rag-owner", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "rag-sensitive-job",
        },
    )
    client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{sensitive_job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="rag-owner", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "rag-sensitive-prepare",
        },
    )
    memory_repo.update_vector_records_status_for_job(
        tenant_id="tenant-croo-local",
        job_id=sensitive_job.json()["id"],
        status="indexed",
    )
    sensitive_record = memory_repo.get_vector_records_for_job(
        tenant_id="tenant-croo-local",
        job_id=sensitive_job.json()["id"],
    )[0]

    forbidden = client.post(
        "/internal/agent-memory/v1/rag/context",
        json={
            "collection": "bob_private_memory_chunks_v1",
            "vector_ids": [owner_record.vector_id],
        },
        headers=signed_headers(user_id="rag-owner", permissions=()),
    )
    allowed = client.post(
        "/internal/agent-memory/v1/rag/context",
        json={
            "collection": "bob_private_memory_chunks_v1",
            "vector_ids": [
                owner_record.vector_id,
                foreign_record.vector_id,
                sensitive_record.vector_id,
                "vec_missing",
            ],
        },
        headers=signed_headers(user_id="rag-owner", permissions=("agent_memory.rag.search",)),
    )
    reordered = client.post(
        "/internal/agent-memory/v1/rag/context",
        json={
            "collection": "bob_private_memory_chunks_v1",
            "vector_ids": [
                "vec_missing",
                sensitive_record.vector_id,
                foreign_record.vector_id,
                owner_record.vector_id,
            ],
        },
        headers=signed_headers(user_id="rag-owner", permissions=("agent_memory.rag.search",)),
    )

    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == {"code": "rag_context_forbidden"}
    assert allowed.status_code == 200
    assert allowed.json()["trace_id"] == "d" * 32
    assert allowed.json()["audit_ref"].startswith("ragctx_")
    assert reordered.status_code == 200
    assert reordered.json()["audit_ref"] != allowed.json()["audit_ref"]
    assert allowed.json()["accepted"] == 1
    assert allowed.json()["rejected"] == 3
    assert allowed.json()["items"][0]["entry_id"] == owner_entry.json()["id"]
    assert allowed.json()["items"][0]["content"] == "Le contexte RAG prive autorise peut nourrir Bob."
    assert allowed.json()["matches"][1]["rejection_code"] == "private_scope_mismatch"
    assert allowed.json()["matches"][2]["rejection_code"] == "rag_sensitivity_forbidden"
    assert allowed.json()["matches"][3]["rejection_code"] == "vector_record_not_found"
    assert "Ce contexte prive etranger" not in str(allowed.json())
    assert "Ce contexte sensible" not in str(allowed.json())
    assert "rag-foreign" not in str(allowed.json())


def test_rag_context_requires_org_permission_for_org_memory(client, memory_repo):
    org_entry = client.post(
        "/internal/agent-memory/v1/organization/entries",
        json=memory_body(
            memory_type="organization_knowledge",
            title="RAG org context",
            content="Le contexte organisationnel exige une permission organisation.",
            sensitivity="internal",
        ),
        headers={
            **signed_headers(permissions=("agent_memory.organization.write",)),
            "Idempotency-Key": "rag-org-source",
        },
    )
    org_job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_organization_knowledge_chunks_v1"},
        headers={
            **signed_headers(permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "rag-org-job",
        },
    )
    client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{org_job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "rag-org-prepare",
        },
    )
    memory_repo.update_vector_records_status_for_job(
        tenant_id="tenant-croo-local",
        job_id=org_job.json()["id"],
        status="indexed",
    )
    org_record = memory_repo.get_vector_records_for_job(
        tenant_id="tenant-croo-local",
        job_id=org_job.json()["id"],
    )[0]

    without_org_permission = client.post(
        "/internal/agent-memory/v1/rag/context",
        json={
            "collection": "bob_organization_knowledge_chunks_v1",
            "vector_ids": [org_record.vector_id],
        },
        headers=signed_headers(permissions=("agent_memory.rag.search",)),
    )
    with_org_permission = client.post(
        "/internal/agent-memory/v1/rag/context",
        json={
            "collection": "bob_organization_knowledge_chunks_v1",
            "vector_ids": [org_record.vector_id],
        },
        headers=signed_headers(
            permissions=("agent_memory.rag.search", "agent_memory.organization.search"),
        ),
    )

    assert without_org_permission.status_code == 200
    assert without_org_permission.json()["accepted"] == 0
    assert without_org_permission.json()["items"] == []
    assert without_org_permission.json()["matches"][0]["rejection_code"] == "organization_scope_forbidden"
    assert "Le contexte organisationnel" not in str(without_org_permission.json())
    assert with_org_permission.status_code == 200
    assert with_org_permission.json()["accepted"] == 1
    assert with_org_permission.json()["items"][0]["entry_id"] == org_entry.json()["id"]
    assert (
        with_org_permission.json()["items"][0]["content"]
        == "Le contexte organisationnel exige une permission organisation."
    )


def test_rag_milvus_context_checks_permission_before_milvus(client, monkeypatch):
    class FailingMilvusSearch:
        def search_candidates(self, **kwargs):
            raise AssertionError("Milvus should not be called without RAG permission")

    monkeypatch.setattr(agent_memory_routes, "MilvusVectorSearch", FailingMilvusSearch)

    response = client.post(
        "/internal/agent-memory/v1/rag/milvus-context",
        json={
            "collection": "bob_private_memory_chunks_v1",
            "query_vector": [0.1, 0.2, 0.3],
            "limit": 3,
        },
        headers=signed_headers(permissions=()),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == {"code": "rag_context_forbidden"}


def test_rag_milvus_context_uses_ranked_candidates_then_postgres_revalidation(
    client,
    memory_repo,
    monkeypatch,
):
    owner_entry = client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(
            title="Milvus owner context",
            content="Le resultat Milvus revalide peut nourrir Bob.",
        ),
        headers={**signed_headers(user_id="milvus-owner"), "Idempotency-Key": "milvus-owner-source"},
    )
    owner_job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1"},
        headers={
            **signed_headers(user_id="milvus-owner", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "milvus-owner-job",
        },
    )
    client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{owner_job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="milvus-owner", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "milvus-owner-prepare",
        },
    )
    memory_repo.update_vector_records_status_for_job(
        tenant_id="tenant-croo-local",
        job_id=owner_job.json()["id"],
        status="indexed",
    )
    owner_record = memory_repo.get_vector_records_for_job(
        tenant_id="tenant-croo-local",
        job_id=owner_job.json()["id"],
    )[0]

    client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(
            title="Milvus foreign context",
            content="Ce resultat Milvus prive etranger ne doit jamais sortir.",
        ),
        headers={**signed_headers(user_id="milvus-foreign"), "Idempotency-Key": "milvus-foreign-source"},
    )
    foreign_job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1"},
        headers={
            **signed_headers(user_id="milvus-foreign", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "milvus-foreign-job",
        },
    )
    client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{foreign_job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="milvus-foreign", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "milvus-foreign-prepare",
        },
    )
    memory_repo.update_vector_records_status_for_job(
        tenant_id="tenant-croo-local",
        job_id=foreign_job.json()["id"],
        status="indexed",
    )
    foreign_record = memory_repo.get_vector_records_for_job(
        tenant_id="tenant-croo-local",
        job_id=foreign_job.json()["id"],
    )[0]

    class FakeMilvusSearch:
        def search_candidates(self, *, config, collection, query_vector, limit):
            assert config.enabled is True
            assert collection == "bob_private_memory_chunks_v1"
            assert len(query_vector) == 3
            assert limit == 3
            return [
                milvus_search.VectorCandidate(
                    vector_id=foreign_record.vector_id,
                    rank=1,
                    distance=0.01,
                ),
                milvus_search.VectorCandidate(
                    vector_id=owner_record.vector_id,
                    rank=2,
                    distance=0.02,
                ),
                milvus_search.VectorCandidate(
                    vector_id="vec_missing",
                    rank=3,
                    distance=0.99,
                ),
            ]

    monkeypatch.setattr(agent_memory_routes, "MilvusVectorSearch", FakeMilvusSearch)
    monkeypatch.setenv("MILVUS_ENABLED", "true")
    monkeypatch.setenv("MILVUS_URI", "http://milvus:19530")
    monkeypatch.setenv("MILVUS_DEFAULT_DIMENSION", "3")

    response = client.post(
        "/internal/agent-memory/v1/rag/milvus-context",
        json={
            "collection": "bob_private_memory_chunks_v1",
            "query_vector": [0.1, 0.2, 0.3],
            "limit": 3,
        },
        headers=signed_headers(user_id="milvus-owner", permissions=("agent_memory.rag.search",)),
    )
    different_query = client.post(
        "/internal/agent-memory/v1/rag/milvus-context",
        json={
            "collection": "bob_private_memory_chunks_v1",
            "query_vector": [0.3, 0.2, 0.1],
            "limit": 3,
        },
        headers=signed_headers(user_id="milvus-owner", permissions=("agent_memory.rag.search",)),
    )

    assert response.status_code == 200
    assert different_query.status_code == 200
    assert different_query.json()["audit_ref"] != response.json()["audit_ref"]
    assert [candidate["rank"] for candidate in response.json()["candidates"]] == [1, 2, 3]
    assert response.json()["accepted"] == 1
    assert response.json()["rejected"] == 2
    assert response.json()["matches"][0]["rejection_code"] == "private_scope_mismatch"
    assert response.json()["items"][0]["entry_id"] == owner_entry.json()["id"]
    assert response.json()["items"][0]["content"] == "Le resultat Milvus revalide peut nourrir Bob."
    assert "Ce resultat Milvus prive etranger" not in str(response.json())
    assert "milvus-foreign" not in str(response.json())


def test_milvus_vector_search_parses_candidates_and_rejects_bad_dimension(monkeypatch):
    config = MilvusConfig(
        enabled=True,
        uri="http://milvus:19530",
        token="placeholder",
        database="default",
        secure=False,
        timeout_seconds=5,
        default_dimension=3,
    )

    class FakeClient:
        def search(self, **kwargs):
            assert kwargs["collection_name"] == "bob_private_memory_chunks_v1"
            assert kwargs["data"] == [[0.1, 0.2, 0.3]]
            assert kwargs["limit"] == 3
            assert kwargs["output_fields"] == []
            return [
                [
                    {"id": "vec_a", "distance": 0.2},
                    {"id": "vec_a", "distance": 0.3},
                    {"entity": {"vector_id": "vec_entity_only"}, "distance": 0.35},
                    {"id": "vec_b", "entity": {"content": "must not leak"}, "distance": "0.4"},
                ]
            ]

    class FakeFactory:
        def __init__(self, *, config):
            self.config = config

        def create(self):
            return FakeClient()

    monkeypatch.setattr(milvus_search, "MilvusClientFactory", FakeFactory)

    candidates = milvus_search.MilvusVectorSearch().search_candidates(
        config=config,
        collection="bob_private_memory_chunks_v1",
        query_vector=[0.1, 0.2, 0.3],
        limit=3,
    )

    assert [candidate.vector_id for candidate in candidates] == ["vec_a", "vec_b"]
    assert [candidate.rank for candidate in candidates] == [1, 4]
    assert candidates[1].distance == 0.4
    with pytest.raises(MilvusConfigError, match="vector_dimension_mismatch"):
        milvus_search.MilvusVectorSearch().search_candidates(
            config=config,
            collection="bob_private_memory_chunks_v1",
            query_vector=[0.1],
            limit=3,
        )


def test_vector_private_job_cannot_be_used_by_another_user(client, memory_repo):
    client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(title="Owner vector source"),
        headers={**signed_headers(user_id="user-owner"), "Idempotency-Key": "vector-owner-source"},
    )
    job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1"},
        headers={
            **signed_headers(user_id="user-owner", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-owner-job",
        },
    )
    foreign_get = client.get(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}",
        headers=signed_headers(user_id="user-foreign", permissions=("agent_memory.vector.manage",)),
    )
    foreign_prepare = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="user-foreign", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-foreign-prepare",
        },
    )
    foreign_rollback = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/rollback",
        headers={
            **signed_headers(user_id="user-foreign", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-foreign-rollback",
        },
    )
    assert job.status_code == 202
    assert foreign_get.status_code == 404
    assert foreign_prepare.status_code == 404
    assert foreign_rollback.status_code == 404
    assert memory_repo.vector_records == {}

    owner_prepare = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="user-owner", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-owner-prepare",
        },
    )

    assert owner_prepare.status_code == 202
    assert owner_prepare.json()["planned_records"] == 1


def test_vector_prepare_dry_run_does_not_store_records(client, memory_repo):
    client.post(
        "/internal/agent-memory/v1/entries",
        json=memory_body(title="Dry run source"),
        headers={**signed_headers(user_id="user-dry"), "Idempotency-Key": "vector-dry-source"},
    )
    job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1", "dry_run": True},
        headers={
            **signed_headers(user_id="user-dry", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-dry-job",
        },
    )
    prepared = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(user_id="user-dry", permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-dry-prepare",
        },
    )

    assert prepared.status_code == 202
    assert prepared.json()["planned_records"] == 1
    assert prepared.json()["stored_records"] == 0
    assert memory_repo.vector_records == {}


def test_vector_prepare_organization_records_use_tenant_scope(client, memory_repo):
    org_entry = client.post(
        "/internal/agent-memory/v1/organization/entries",
        json=memory_body(memory_type="organization_knowledge", sensitivity="internal"),
        headers={
            **signed_headers(permissions=("agent_memory.organization.write",)),
            "Idempotency-Key": "vector-org-source",
        },
    )
    job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_organization_knowledge_chunks_v1"},
        headers={
            **signed_headers(permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-org-job",
        },
    )
    prepared = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-org-prepare",
        },
    )

    records = list(memory_repo.vector_records.values())
    assert org_entry.status_code == 201
    assert prepared.status_code == 202
    assert prepared.json()["planned_records"] == 1
    assert records[0].source_id == org_entry.json()["id"]
    assert records[0].user_id is None
    assert records[0].scope_type == "organization"
    assert records[0].scope_key.startswith("sk_")


def test_vector_prepare_errors_and_empty_source_ref(client):
    job = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1", "source_ref": "missing-entry"},
        headers={
            **signed_headers(permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-empty-source-job",
        },
    )
    empty_prepare = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-empty-source-prepare",
        },
    )
    missing = client.post(
        "/internal/agent-memory/v1/vector-index/jobs/missing/prepare",
        json={"limit": 10},
        headers={
            **signed_headers(permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-missing-prepare",
        },
    )
    forbidden = client.post(
        f"/internal/agent-memory/v1/vector-index/jobs/{job.json()['id']}/prepare",
        json={"limit": 10},
        headers={**signed_headers(), "Idempotency-Key": "vector-forbidden-prepare"},
    )

    assert empty_prepare.status_code == 202
    assert empty_prepare.json()["planned_records"] == 0
    assert empty_prepare.json()["stored_records"] == 0
    assert empty_prepare.json()["job"]["status"] == "queued"
    assert missing.status_code == 404
    assert missing.json()["detail"] == {"code": "vector_index_job_not_found"}
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == {"code": "vector_index_forbidden"}


def test_vector_rebuild_rejects_invalid_collection_and_scope(client):
    headers = {
        **signed_headers(permissions=("agent_memory.vector.manage",)),
        "Idempotency-Key": "vector-invalid",
    }
    unsupported = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "unknown_collection"},
        headers=headers,
    )
    mismatch = client.post(
        "/internal/agent-memory/v1/vector-index/rebuild",
        json={"collection": "bob_private_memory_chunks_v1", "scope_type": "organization"},
        headers={
            **signed_headers(permissions=("agent_memory.vector.manage",)),
            "Idempotency-Key": "vector-mismatch",
        },
    )

    assert unsupported.status_code == 400
    assert unsupported.json()["detail"] == {"code": "vector_collection_not_supported"}
    assert mismatch.status_code == 400
    assert mismatch.json()["detail"] == {"code": "vector_scope_mismatch"}


def test_vector_job_read_and_rollback_errors(client):
    missing = client.get(
        "/internal/agent-memory/v1/vector-index/jobs/missing",
        headers=signed_headers(permissions=("agent_memory.vector.manage",)),
    )
    forbidden_get = client.get(
        "/internal/agent-memory/v1/vector-index/jobs/missing",
        headers=signed_headers(),
    )
    forbidden_rollback = client.post(
        "/internal/agent-memory/v1/vector-index/jobs/missing/rollback",
        headers={**signed_headers(), "Idempotency-Key": "vector-rollback-denied"},
    )
    missing_prepare_header = client.post(
        "/internal/agent-memory/v1/vector-index/jobs/missing/prepare",
        json={"limit": 10},
        headers=signed_headers(permissions=("agent_memory.vector.manage",)),
    )

    assert missing.status_code == 404
    assert missing.json()["detail"] == {"code": "vector_index_job_not_found"}
    assert forbidden_get.status_code == 403
    assert forbidden_get.json()["detail"] == {"code": "vector_index_forbidden"}
    assert forbidden_rollback.status_code == 403
    assert forbidden_rollback.json()["detail"] == {"code": "vector_index_forbidden"}
    assert missing_prepare_header.status_code == 422


def test_python_package_contract_loads_memory_components():
    from agent_memory_backend_api.contract import CONTRACT_VERSION, load_memory_components

    assert CONTRACT_VERSION == "0.1.0"
    assert len(load_memory_components()) == 6
