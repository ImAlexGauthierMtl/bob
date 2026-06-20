from datetime import datetime, timezone

from fastapi.testclient import TestClient
import httpx
import pytest

import main
from app.application.use_cases.agent_runtime_use_cases import AgentRuntimeUseCases
from app.domain import AgentConfirmation, InternalContext, RuntimeToolCall
from app.infrastructure.persistence.in_memory_agent_runtime_repository import (
    InMemoryAgentRuntimeRepository,
)
from app.infrastructure.providers import factory as provider_factory
from app.infrastructure.providers.fireworks_provider import FireworksRuntimeProvider, _to_tool_call
from app.infrastructure.providers.local_provider import LocalRuntimeProvider
from app.infrastructure.tools.local_registry import LocalRuntimeToolRegistry
from app.presentation.routes import agent_runtime_routes
from shared.infrastructure import InternalSessionContext, InternalSessionContextSigner


@pytest.fixture()
def runtime_repo():
    return InMemoryAgentRuntimeRepository()


@pytest.fixture()
def client(runtime_repo):
    use_cases = AgentRuntimeUseCases(
        repo=runtime_repo,
        runtime_provider=LocalRuntimeProvider(),
        tool_registry=LocalRuntimeToolRegistry(),
    )
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
    assert payload["mode"] == "local_runtime"
    assert payload["trace_id"] == "c" * 32
    assert "runtime agentique CDE" in payload["assistant_content"]
    assert payload["narration_steps"][0]["label"] == "demande_recue"
    assert payload["metadata"]["provider"] == "local"
    assert payload["metadata"]["model"] == "bob-local-runtime"
    assert payload["metadata"]["tool_calls"][0]["tool"] == "bob_runtime_status"
    assert payload["actions"][0]["tool"] == "bob_runtime_status"

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


def test_runtime_settings_expose_backend_catalog_and_mcp_families(client):
    response = client.get(
        "/internal/agent-runtime/v1/settings",
        headers=signed_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "agent-runtime-backend-api"
    assert payload["providers"][0]["model"] == "accounts/fireworks/models/kimi-k2p7-code"
    assert payload["mcp"]["tool_gating_required"] is True
    assert "assistant-memory" in {family["family"] for family in payload["mcp"]["families"]}
    assert "factory" in {tool["family"] for tool in payload["tools"]}


def test_runtime_settings_catalog_mutations_are_scoped_and_idempotent(client):
    headers = {**signed_headers(user_id="user-settings-a"), "Idempotency-Key": "tool-create-1"}
    first = client.post(
        "/internal/agent-runtime/v1/settings/tools",
        json={"name": "factory_status", "family": "factory", "risk": "read"},
        headers=headers,
    )
    replay = client.post(
        "/internal/agent-runtime/v1/settings/tools",
        json={"name": "factory_status", "family": "factory", "risk": "read"},
        headers=headers,
    )
    conflict = client.post(
        "/internal/agent-runtime/v1/settings/tools",
        json={"name": "factory_status_changed", "family": "factory", "risk": "read"},
        headers=headers,
    )
    scoped = client.get(
        "/internal/agent-runtime/v1/settings",
        headers=signed_headers(user_id="user-settings-b"),
    )
    missing_name = client.post(
        "/internal/agent-runtime/v1/settings/skills",
        json={"description": "bad"},
        headers={**signed_headers(user_id="user-settings-a"), "Idempotency-Key": "bad-skill"},
    )

    assert first.status_code == 201
    assert first.json()["item"]["name"] == "factory_status"
    assert replay.status_code == 201
    assert replay.json() == first.json()
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == {"code": "idempotency_conflict"}
    assert "factory_status" not in {tool["name"] for tool in scoped.json()["tools"]}
    assert missing_name.status_code == 422


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


@pytest.mark.asyncio
async def test_local_registry_executes_runtime_memory_and_rejects_unknown_tools():
    registry = LocalRuntimeToolRegistry()
    context = InternalContext(
        tenant_id="tenant-croo-local",
        user_id="user-alex-local",
        trace_id="d" * 32,
        permissions=("bob_chat.use",),
        roles=("admin",),
    )
    metadata = {
        "memory_context": {
            "private": [{"id": "mem-1", "title": "Style", "memory_type": "preference"}],
            "organization": [{"id": "org-1", "title": "Procedure", "memory_type": "procedure"}],
            "degraded": ["vector_unavailable"],
            "source": "agent-memory-backend-api",
        }
    }

    tools = registry.list_tools(prompt="Quel est ton runtime?", context=context, metadata=metadata)
    runtime_status = await registry.execute(
        call=RuntimeToolCall(
            id="call-runtime",
            name="bob_runtime_status",
            arguments={"include_tools": False},
        ),
        context=context,
        metadata=metadata,
    )
    memory_summary = await registry.execute(
        call=RuntimeToolCall(
            id="call-memory",
            name="bob_memory_context_summary",
            arguments={"max_items": 1},
        ),
        context=context,
        metadata=metadata,
    )
    rejected = await registry.execute(
        call=RuntimeToolCall(id="call-bad", name="missing_tool", arguments={}),
        context=context,
        metadata=metadata,
    )

    assert tools[0]["function"]["name"] == "bob_runtime_status"
    assert runtime_status.status == "completed"
    assert "available_tool_families" not in runtime_status.content
    assert memory_summary.status == "completed"
    assert "mem-1" in memory_summary.content
    assert rejected.status == "rejected"


def test_provider_factory_selects_local_fireworks_and_rejects_missing_key(monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_PROVIDER", "local")
    assert isinstance(provider_factory.create_runtime_provider(), LocalRuntimeProvider)

    monkeypatch.setenv("AGENT_RUNTIME_PROVIDER", "fireworks")
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        provider_factory.create_runtime_provider()

    monkeypatch.setenv("FIREWORKS_API_KEY", "test-key")
    provider = provider_factory.create_runtime_provider()
    assert isinstance(provider, FireworksRuntimeProvider)


@pytest.mark.asyncio
async def test_fireworks_provider_maps_chat_completion_tool_calls(monkeypatch):
    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None, headers=None):
            assert url == "https://fireworks.example/chat/completions"
            assert headers["Authorization"] == "Bearer key"
            assert json["model"] == "accounts/fireworks/models/kimi-k2p7-code"
            assert json["tool_choice"] == "auto"
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "choices": [
                        {
                            "finish_reason": "tool_calls",
                            "message": {
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "tool-1",
                                        "function": {
                                            "name": "bob_runtime_status",
                                            "arguments": "{\"include_tools\": true}",
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                    "usage": {"prompt_tokens": 10},
                },
            )

    monkeypatch.setattr("app.infrastructure.providers.fireworks_provider.httpx.AsyncClient", FakeAsyncClient)
    provider = FireworksRuntimeProvider(
        api_key="key",
        base_url="https://fireworks.example",
        model="accounts/fireworks/models/kimi-k2p7-code",
        temperature=0.1,
        top_p=0.8,
        timeout_seconds=12,
    )

    result = await provider.complete(
        messages=[{"role": "user", "content": "Bonjour"}],
        tools=[{"type": "function", "function": {"name": "bob_runtime_status", "parameters": {}}}],
        trace_id="e" * 32,
    )
    invalid_arguments = _to_tool_call(
        index=2,
        raw_tool_call={"function": {"name": "bad_args", "arguments": "{not-json"}},
    )

    assert result.mode == "provider_fireworks"
    assert result.tool_calls[0].name == "bob_runtime_status"
    assert result.tool_calls[0].arguments == {"include_tools": True}
    assert result.raw_metadata["usage"]["prompt_tokens"] == 10
    assert invalid_arguments.arguments == {"raw": "{not-json"}


def test_python_package_contract_loads_runtime_components():
    from agent_runtime_backend_api.contract import CONTRACT_VERSION, load_runtime_components

    assert CONTRACT_VERSION == "0.1.0"
    assert len(load_runtime_components()) == 4
