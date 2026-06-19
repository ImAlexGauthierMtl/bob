from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

import main
from app.application.use_cases.agent_runtime_use_cases import AgentRuntimeUseCases
from app.domain import AgentConfirmation
from app.infrastructure.persistence.in_memory_agent_runtime_repository import (
    InMemoryAgentRuntimeRepository,
)
from app.presentation.routes import agent_runtime_routes
from shared.infrastructure import InternalSessionContext, InternalSessionContextSigner


@pytest.fixture()
def runtime_repo():
    return InMemoryAgentRuntimeRepository()


@pytest.fixture()
def client(runtime_repo):
    use_cases = AgentRuntimeUseCases(repo=runtime_repo)
    main.app.dependency_overrides[agent_runtime_routes.get_agent_runtime_use_cases] = lambda: use_cases
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


def signed_headers(*, tenant_id="tenant-croo-local", user_id="user-alex-local"):
    signer = InternalSessionContextSigner(
        "dev-internal-session-secret-not-for-production",
        kid="internal-session-dev",
    )
    context = InternalSessionContext(
        tenant_id=tenant_id,
        user_id=user_id,
        session_id="sess-bob-cloud-stub",
        trace_id="c" * 32,
        permissions=("bob_chat.use",),
        entitlements=("bob_chat.use",),
        roles=("admin",),
    )
    return {
        "X-Session-Context": signer.issue(context),
        "X-Trace-Id": "c" * 32,
    }


def run_body():
    return {
        "session_id": "chat-local-1",
        "input_message_id": "msg-user-1",
        "prompt": "Montre mes suivis prioritaires",
        "channel": "workspace",
        "metadata": {"source": "bob-chat-b4f-api"},
    }


def test_monitoring_endpoints_do_not_require_internal_context(client):
    for path in ["/health", "/readiness", "/liveness", "/startup", "/metrics"]:
        response = client.get(path)
        assert response.status_code == 200


def test_internal_routes_require_signed_context(client):
    response = client.post(
        "/internal/agent-runtime/v1/runs",
        json=run_body(),
        headers={"Idempotency-Key": "run-1"},
    )

    assert response.status_code == 401


def test_create_run_and_fetch_it(client):
    created = client.post(
        "/internal/agent-runtime/v1/runs",
        json=run_body(),
        headers={**signed_headers(), "Idempotency-Key": "run-1"},
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["id"].startswith("run_")
    assert payload["status"] == "completed"
    assert payload["mode"] == "contract_seed"
    assert payload["trace_id"] == "c" * 32
    assert "Bob a pris en charge" in payload["assistant_content"]
    assert payload["narration_steps"][0]["label"] == "demande_recue"

    fetched = client.get(
        f"/internal/agent-runtime/v1/runs/{payload['id']}",
        headers=signed_headers(),
    )

    assert fetched.status_code == 200
    assert fetched.json() == payload


def test_run_idempotency_replays_same_run(client):
    first = client.post(
        "/internal/agent-runtime/v1/runs",
        json=run_body(),
        headers={**signed_headers(), "Idempotency-Key": "same-run"},
    )
    second = client.post(
        "/internal/agent-runtime/v1/runs",
        json={**run_body(), "prompt": "Payload change"},
        headers={**signed_headers(), "Idempotency-Key": "same-run"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json() == second.json()


def test_run_scope_is_tenant_and_user_bound(client):
    created = client.post(
        "/internal/agent-runtime/v1/runs",
        json=run_body(),
        headers={**signed_headers(user_id="user-a"), "Idempotency-Key": "scope-run"},
    )
    run_id = created.json()["id"]

    foreign_user = client.get(
        f"/internal/agent-runtime/v1/runs/{run_id}",
        headers=signed_headers(user_id="user-b"),
    )
    foreign_tenant = client.get(
        f"/internal/agent-runtime/v1/runs/{run_id}",
        headers=signed_headers(tenant_id="tenant-other", user_id="user-a"),
    )

    assert foreign_user.status_code == 404
    assert foreign_tenant.status_code == 404


def test_completed_run_is_not_cancelable(client):
    created = client.post(
        "/internal/agent-runtime/v1/runs",
        json=run_body(),
        headers={**signed_headers(), "Idempotency-Key": "cancel-run"},
    )
    run_id = created.json()["id"]

    cancelled = client.post(
        f"/internal/agent-runtime/v1/runs/{run_id}/cancel",
        headers=signed_headers(),
    )

    assert cancelled.status_code == 409
    assert cancelled.json()["detail"] == {"code": "run_not_cancelable"}


def test_confirmation_resolution_contract(client, runtime_repo):
    created = client.post(
        "/internal/agent-runtime/v1/runs",
        json=run_body(),
        headers={**signed_headers(), "Idempotency-Key": "confirmation-run"},
    )
    run_id = created.json()["id"]
    runtime_repo.confirmations["confirm-1"] = AgentConfirmation(
        id="confirm-1",
        run_id=run_id,
        tenant_id="tenant-croo-local",
        user_id="user-alex-local",
        status="pending",
        label="Confirmer action test",
        created_at=datetime.now(timezone.utc),
    )

    confirmed = client.post(
        f"/internal/agent-runtime/v1/runs/{run_id}/confirmations/confirm-1/confirm",
        headers=signed_headers(),
    )
    repeated = client.post(
        f"/internal/agent-runtime/v1/runs/{run_id}/confirmations/confirm-1/cancel",
        headers=signed_headers(),
    )
    missing = client.post(
        f"/internal/agent-runtime/v1/runs/{run_id}/confirmations/missing/confirm",
        headers=signed_headers(),
    )

    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"
    assert repeated.status_code == 409
    assert repeated.json()["detail"] == {"code": "confirmation_already_resolved"}
    assert missing.status_code == 404
    assert missing.json()["detail"] == {"code": "confirmation_not_found"}


def test_python_package_contract_loads_runtime_components():
    from agent_runtime_backend_api.contract import CONTRACT_VERSION, load_runtime_components

    assert CONTRACT_VERSION == "0.1.0"
    assert len(load_runtime_components()) == 4
