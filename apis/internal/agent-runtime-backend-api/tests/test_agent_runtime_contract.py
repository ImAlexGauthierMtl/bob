from copy import deepcopy
from datetime import datetime, timezone

from fastapi.testclient import TestClient
import httpx
import pytest

import main
from app.application.use_cases.agent_runtime_use_cases import AgentRuntimeUseCases
from app.domain import AgentConfirmation, InternalContext, RuntimeModelResult, RuntimeToolCall
from app.infrastructure.persistence.in_memory_agent_runtime_repository import (
    InMemoryAgentRuntimeRepository,
)
from app.infrastructure.providers import factory as provider_factory
from app.infrastructure.providers.fireworks_provider import FireworksRuntimeProvider, _to_tool_call
from app.infrastructure.providers.local_provider import LocalRuntimeProvider
from app.infrastructure.tools.factory_supabase_adapter import (
    FactorySupabaseAdapter,
    FactorySupabaseAdapterError,
)
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


class CapturingRuntimeProvider:
    def __init__(self) -> None:
        self.messages = []
        self.tools = []

    async def complete(self, *, messages, tools, trace_id):
        self.messages.append(messages)
        self.tools.append(tools)
        return RuntimeModelResult(
            content="Captured prompt",
            provider="capture",
            model="capture-model",
            mode="capture_runtime",
            raw_metadata={"trace_id": trace_id},
        )


class SequencedRuntimeProvider:
    def __init__(self, results: list[RuntimeModelResult]) -> None:
        self.results = results
        self.messages = []
        self.tools = []
        self.calls = 0

    async def complete(self, *, messages, tools, trace_id):
        self.calls += 1
        self.messages.append(deepcopy(messages))
        self.tools.append(deepcopy(tools))
        index = min(self.calls - 1, len(self.results) - 1)
        return self.results[index]


class FailingRuntimeProvider:
    def __init__(self, *, fail_on_call: int, before_failure: RuntimeModelResult | None = None) -> None:
        self.fail_on_call = fail_on_call
        self.before_failure = before_failure
        self.calls = 0

    async def complete(self, *, messages, tools, trace_id):
        self.calls += 1
        if self.calls == self.fail_on_call:
            raise RuntimeError("fireworks token=should-not-leak")
        if self.before_failure is not None:
            return self.before_failure
        return RuntimeModelResult(
            content="Provider OK",
            provider="failing-test",
            model="failing-test-model",
            mode="failing_test",
        )


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


def test_create_run_can_call_mcp_gateway_for_tool_family(client):
    created = client.post(
        "/internal/agent-runtime/v1/runs",
        json={**run_body(), "prompt": "Charge la famille MCP Factory et decris ses capacites."},
        headers={**signed_headers(), "Idempotency-Key": "mcp-gateway-run"},
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["metadata"]["tool_calls"][0]["tool"] == "bob_mcp_gateway"
    assert payload["actions"][0]["metadata"]["family"] == "factory"
    assert payload["actions"][0]["metadata"]["operation"] == "describe_family"
    assert "factory-supabase" in payload["actions"][0]["content"]
    assert "bob_mcp_gateway" in payload["assistant_content"]


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
    skill_ids = {skill["id"] for skill in payload["skills"]}
    assert len(payload["skills"]) >= 50
    assert "skill-mcp-capability-routing" in skill_ids
    assert "skill-source-driven-development" in skill_ids
    default_agent = next(agent for agent in payload["agents"] if agent["id"] == "agent-bob-orchestrator")
    assert "skill-mcp-capability-routing" in default_agent["skills"]
    assert payload["mcp"]["tool_gating_required"] is True
    assert "assistant-memory" in {family["family"] for family in payload["mcp"]["families"]}
    assert "slack.draft-send" in {capability["qualified_id"] for capability in payload["mcp"]["capabilities"]}
    assert "factory.requests-queues" in {capability["qualified_id"] for capability in payload["mcp"]["capabilities"]}
    assert "factory" in {tool["family"] for tool in payload["tools"]}
    assert "bob_mcp_gateway" in {tool["name"] for tool in payload["tools"]}
    assert "slack.draft-send" in {tool["name"] for tool in payload["tools"]}
    factory_family = next(family for family in payload["mcp"]["families"] if family["family"] == "factory")
    assert factory_family["capability_count"] >= 9
    assert any(item["file"] == "requests-queues.md" for item in factory_family["capability_items"])
    legacy_agent_name = "".join(("libre", "chat"))
    legacy_graph_name = "".join(("lang", "graph"))
    assert legacy_agent_name not in str(payload).lower()
    assert legacy_graph_name not in str(payload).lower()
    inventory = payload["conversion_inventory"]
    assert inventory["target"] == "bob-cde-runtime"
    assert inventory["active_model"] == "accounts/fireworks/models/kimi-k2p7-code"
    assert {module["id"] for module in inventory["settings_modules"]} >= {
        "agents",
        "skills",
        "tools_mcp",
        "memory_rag_vectors",
        "rbac_entitlements",
    }
    assert {
        surface["id"]: surface["status"]
        for surface in inventory["surfaces"]
    }["bob_control_center"] == "legacy_settings_surface_active"
    assert {
        surface["id"]: surface["status"]
        for surface in inventory["surfaces"]
    }["legacy_graph_runtime"] == "removed_from_cde_runtime"


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
    assert "factory_status" in {tool["name"] for tool in scoped.json()["tools"]}
    assert missing_name.status_code == 422


def test_run_resolves_selected_agent_skills_and_tools_from_runtime_settings(client):
    settings_headers = signed_headers(user_id="user-runtime-settings-admin")
    run_headers = signed_headers(user_id="user-runtime-chat")
    skill = client.post(
        "/internal/agent-runtime/v1/settings/skills",
        json={
            "id": "skill-cde-sales-context",
            "name": "CDE Sales Context",
            "description": "Qualification client depuis CDE.",
        },
        headers={**settings_headers, "Idempotency-Key": "skill-cde-sales-context"},
    )
    tool = client.post(
        "/internal/agent-runtime/v1/settings/tools",
        json={
            "id": "tool-cde-factory-read",
            "name": "factory.requests-queues",
            "family": "factory",
            "risk": "read",
        },
        headers={**settings_headers, "Idempotency-Key": "tool-cde-factory-read"},
    )
    agent = client.post(
        "/internal/agent-runtime/v1/settings/agents",
        json={
            "id": "agent-cde-sales",
            "name": "Bob Sales",
            "description": "Agent de suivi commercial CDE.",
            "provider_id": "fireworks-kimi",
            "status": "active",
            "skills": ["skill-cde-sales-context"],
            "tools": ["tool-cde-factory-read"],
        },
        headers={**settings_headers, "Idempotency-Key": "agent-cde-sales"},
    )

    created = client.post(
        "/internal/agent-runtime/v1/runs",
        json={
            **run_body(),
            "metadata": {
                "source": "bob-chat-b4f-api",
                "agent_id": "agent-cde-sales",
            },
        },
        headers={**run_headers, "Idempotency-Key": "selected-agent-run"},
    )

    assert skill.status_code == 201
    assert tool.status_code == 201
    assert agent.status_code == 201
    assert created.status_code == 201
    runtime_catalog = created.json()["metadata"]["runtime_catalog"]
    assert runtime_catalog["requested_agent_id"] == "agent-cde-sales"
    assert runtime_catalog["selection_status"] == "requested"
    assert runtime_catalog["agent"]["id"] == "agent-cde-sales"
    assert [item["id"] for item in runtime_catalog["skills"]] == ["skill-cde-sales-context"]
    assert [item["id"] for item in runtime_catalog["tools"]] == ["tool-cde-factory-read"]


def test_selected_agent_tools_gate_runtime_tool_calls(client):
    headers = signed_headers(user_id="user-runtime-tool-gating")
    client.post(
        "/internal/agent-runtime/v1/settings/tools",
        json={
            "id": "tool-cde-factory-read",
            "name": "factory.requests-queues",
            "family": "factory",
            "risk": "read",
        },
        headers={**headers, "Idempotency-Key": "tool-gated-factory"},
    )
    client.post(
        "/internal/agent-runtime/v1/settings/agents",
        json={
            "id": "agent-cde-factory-only",
            "name": "Bob Factory Only",
            "description": "Agent limite a la gateway Factory.",
            "provider_id": "fireworks-kimi",
            "status": "active",
            "skills": [],
            "tools": ["tool-cde-factory-read"],
        },
        headers={**headers, "Idempotency-Key": "agent-gated-factory"},
    )

    created = client.post(
        "/internal/agent-runtime/v1/runs",
        json={
            **run_body(),
            "prompt": "Liste la queue Factory NEW par projet.",
            "metadata": {
                "source": "bob-chat-b4f-api",
                "agent_id": "agent-cde-factory-only",
            },
        },
        headers={**headers, "Idempotency-Key": "selected-agent-gated-tool-run"},
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["metadata"]["runtime_catalog"]["agent"]["id"] == "agent-cde-factory-only"
    assert payload["metadata"]["tool_calls"][0]["tool"] == "bob_mcp_gateway"
    assert payload["actions"][0]["metadata"]["family"] == "factory"
    assert "bob_runtime_status" not in {call["tool"] for call in payload["metadata"]["tool_calls"]}


def test_http_catalog_source_and_redaction_reach_runtime_prompt():
    repo = InMemoryAgentRuntimeRepository()
    provider = CapturingRuntimeProvider()
    use_cases = AgentRuntimeUseCases(
        repo=repo,
        runtime_provider=provider,
        tool_registry=LocalRuntimeToolRegistry(),
    )
    main.app.dependency_overrides[agent_runtime_routes.get_agent_runtime_use_cases] = lambda: use_cases
    try:
        with TestClient(main.app) as test_client:
            headers = signed_headers(user_id="user-http-skill-prompt")
            skill = test_client.post(
                "/internal/agent-runtime/v1/settings/skills",
                json={
                    "id": "skill-http-follow-up",
                    "name": "HTTP Follow-up",
                    "description": "Guide le suivi client. token=should-not-leak",
                    "scope": "shared_clean",
                    "source": "croo-agentic/skills/http-follow-up.md",
                },
                headers={**headers, "Idempotency-Key": "skill-http-follow-up"},
            )
            tool = test_client.post(
                "/internal/agent-runtime/v1/settings/tools",
                json={
                    "id": "tool-http-factory",
                    "name": "factory.requests-queues",
                    "description": "Lit Factory avec api_key=hidden-value",
                    "family": "factory",
                    "risk": "read",
                    "execution": "internal_gateway",
                },
                headers={**headers, "Idempotency-Key": "tool-http-factory"},
            )
            agent = test_client.post(
                "/internal/agent-runtime/v1/settings/agents",
                json={
                    "id": "agent-http-follow-up",
                    "name": "Bob HTTP Follow-up token=agent-leak",
                    "status": "active",
                    "skills": ["skill-http-follow-up"],
                    "tools": ["tool-http-factory"],
                },
                headers={**headers, "Idempotency-Key": "agent-http-follow-up"},
            )
            run = test_client.post(
                "/internal/agent-runtime/v1/runs",
                json={
                    **run_body(),
                    "metadata": {
                        "source": "bob-chat-b4f-api",
                        "agent_id": "agent-http-follow-up",
                    },
                },
                headers={**headers, "Idempotency-Key": "run-http-follow-up"},
            )
    finally:
        main.app.dependency_overrides.clear()

    assert skill.status_code == 201
    assert tool.status_code == 201
    assert agent.status_code == 201
    assert run.status_code == 201
    system_prompt = provider.messages[0][0]["content"]
    assert "agent=Bob HTTP Follow-up token=[redacted] (agent-http-follow-up)" in system_prompt
    assert "source=croo-agentic/skills/http-follow-up.md" in system_prompt
    assert "token=[redacted]" in system_prompt
    assert "api_key=[redacted]" in system_prompt
    assert "should-not-leak" not in system_prompt
    assert "hidden-value" not in system_prompt
    assert "agent-leak" not in system_prompt


@pytest.mark.asyncio
async def test_selected_skill_and_tool_details_are_injected_in_runtime_prompt():
    repo = InMemoryAgentRuntimeRepository()
    provider = CapturingRuntimeProvider()
    use_cases = AgentRuntimeUseCases(
        repo=repo,
        runtime_provider=provider,
        tool_registry=LocalRuntimeToolRegistry(),
    )
    context = InternalContext(
        tenant_id="tenant-croo-local",
        user_id="user-skill-prompt",
        trace_id="a" * 32,
        permissions=("bob_chat.use", "agent.run.create"),
        roles=("admin",),
    )

    await use_cases.create_runtime_catalog_item(
        context=context,
        collection="skills",
        payload={
            "id": "skill-cde-follow-up",
            "name": "CDE Follow-up",
            "description": "Qualifie le prochain suivi client avec source et date.",
            "scope": "shared_clean",
            "source": "croo-agentic/skills/follow-up.md",
        },
        idempotency_key="skill-cde-follow-up",
    )
    await use_cases.create_runtime_catalog_item(
        context=context,
        collection="tools",
        payload={
            "id": "tool-factory-queue",
            "name": "factory.requests-queues",
            "description": "Lit les demandes Factory par queue et projet.",
            "family": "factory",
            "risk": "read",
            "execution": "internal_gateway",
        },
        idempotency_key="tool-factory-queue",
    )
    await use_cases.create_runtime_catalog_item(
        context=context,
        collection="agents",
        payload={
            "id": "agent-cde-follow-up",
            "name": "Bob Follow-up",
            "status": "active",
            "skills": ["skill-cde-follow-up"],
            "tools": ["tool-factory-queue"],
        },
        idempotency_key="agent-cde-follow-up",
    )

    run = await use_cases.create_run(
        context=context,
        session_id="session-skill-prompt",
        input_message_id="msg-skill-prompt",
        prompt="Prepare le suivi et verifie la queue Factory.",
        channel="workspace",
        metadata={"source": "bob-chat-b4f-api", "agent_id": "agent-cde-follow-up"},
        idempotency_key="run-skill-prompt",
    )

    system_prompt = provider.messages[0][0]["content"]
    assert run.mode == "capture_runtime"
    assert "agent=Bob Follow-up (agent-cde-follow-up)" in system_prompt
    assert "CDE Follow-up" in system_prompt
    assert "Qualifie le prochain suivi client avec source et date." in system_prompt
    assert "source=croo-agentic/skills/follow-up.md" in system_prompt
    assert "factory.requests-queues" in system_prompt
    assert "family=factory" in system_prompt
    assert "risk=read" in system_prompt
    assert "execution=internal_gateway" in system_prompt


@pytest.mark.asyncio
async def test_runtime_executes_multiple_tool_call_turns_before_final_answer():
    repo = InMemoryAgentRuntimeRepository()
    provider = SequencedRuntimeProvider(
        [
            RuntimeModelResult(
                content="",
                provider="sequence",
                model="sequence-model",
                mode="sequence_runtime",
                tool_calls=[
                    RuntimeToolCall(
                        id="call-runtime-status",
                        name="bob_runtime_status",
                        arguments={"include_tools": False},
                    )
                ],
            ),
            RuntimeModelResult(
                content="",
                provider="sequence",
                model="sequence-model",
                mode="sequence_runtime",
                tool_calls=[
                    RuntimeToolCall(
                        id="call-memory",
                        name="bob_memory_context_summary",
                        arguments={"max_items": 1},
                    )
                ],
            ),
            RuntimeModelResult(
                content="Synthese finale apres deux outils.",
                provider="sequence",
                model="sequence-model",
                mode="sequence_runtime",
                raw_metadata={"phase": "final"},
            ),
        ]
    )
    use_cases = AgentRuntimeUseCases(
        repo=repo,
        runtime_provider=provider,
        tool_registry=LocalRuntimeToolRegistry(),
    )
    context = InternalContext(
        tenant_id="tenant-croo-local",
        user_id="user-multi-tool",
        trace_id="b" * 32,
        permissions=("bob_chat.use", "agent.run.create"),
        roles=("admin",),
    )

    run = await use_cases.create_run(
        context=context,
        session_id="session-multi-tool",
        input_message_id="msg-multi-tool",
        prompt="Resume le runtime puis la memoire.",
        channel="workspace",
        metadata={
            "source": "bob-chat-b4f-api",
            "memory_context": {
                "private": [{"id": "mem-1", "title": "Preference", "memory_type": "note"}],
                "organization": [],
            },
        },
        idempotency_key="run-multi-tool",
    )

    assert provider.calls == 3
    assert run.assistant_content == "Synthese finale apres deux outils."
    assert [action["tool"] for action in run.actions] == [
        "bob_runtime_status",
        "bob_memory_context_summary",
    ]
    assert run.metadata["tool_loop"] == {
        "provider_iterations": 3,
        "executed_tool_calls": 2,
        "max_provider_iterations": 5,
        "max_total_tool_calls": 12,
        "limit_reached": False,
    }
    assert any(message.get("role") == "tool" for message in provider.messages[1])
    assert any(message.get("role") == "tool" for message in provider.messages[2])


@pytest.mark.asyncio
async def test_runtime_tool_loop_stops_at_provider_iteration_limit():
    repo = InMemoryAgentRuntimeRepository()
    provider = SequencedRuntimeProvider(
        [
            RuntimeModelResult(
                content="",
                provider="sequence",
                model="sequence-model",
                mode="sequence_runtime",
                tool_calls=[
                    RuntimeToolCall(
                        id=f"call-runtime-status-{index}",
                        name="bob_runtime_status",
                        arguments={"include_tools": False},
                    )
                ],
            )
            for index in range(8)
        ]
    )
    use_cases = AgentRuntimeUseCases(
        repo=repo,
        runtime_provider=provider,
        tool_registry=LocalRuntimeToolRegistry(),
    )
    context = InternalContext(
        tenant_id="tenant-croo-local",
        user_id="user-loop-limit",
        trace_id="f" * 32,
        permissions=("bob_chat.use", "agent.run.create"),
        roles=("admin",),
    )

    run = await use_cases.create_run(
        context=context,
        session_id="session-loop-limit",
        input_message_id="msg-loop-limit",
        prompt="Continue toujours a verifier le runtime.",
        channel="workspace",
        metadata={"source": "bob-chat-b4f-api"},
        idempotency_key="run-loop-limit",
    )

    assert provider.calls == 5
    assert len(run.actions) == 4
    assert run.metadata["tool_loop"]["provider_iterations"] == 5
    assert run.metadata["tool_loop"]["executed_tool_calls"] == 4
    assert run.metadata["tool_loop"]["limit_reached"] is True
    assert "interrompu la boucle d'outils" in run.assistant_content
    assert run.narration_steps[-2] == {
        "label": "tool_loop_limit_reached",
        "status": "degraded",
        "visible": True,
    }


@pytest.mark.asyncio
async def test_runtime_tool_loop_caps_calls_per_turn_and_total_calls():
    repo = InMemoryAgentRuntimeRepository()
    repeated_results = []
    for turn in range(8):
        repeated_results.append(
            RuntimeModelResult(
                content="",
                provider="sequence",
                model="sequence-model",
                mode="sequence_runtime",
                tool_calls=[
                    RuntimeToolCall(
                        id=f"call-runtime-status-{turn}-{index}",
                        name="bob_runtime_status",
                        arguments={"include_tools": False},
                    )
                    for index in range(4)
                ],
            )
        )
    provider = SequencedRuntimeProvider(repeated_results)
    use_cases = AgentRuntimeUseCases(
        repo=repo,
        runtime_provider=provider,
        tool_registry=LocalRuntimeToolRegistry(),
    )
    context = InternalContext(
        tenant_id="tenant-croo-local",
        user_id="user-loop-total-limit",
        trace_id="9" * 32,
        permissions=("bob_chat.use", "agent.run.create"),
        roles=("admin",),
    )

    run = await use_cases.create_run(
        context=context,
        session_id="session-loop-total-limit",
        input_message_id="msg-loop-total-limit",
        prompt="Appelle trop d'outils pour verifier les plafonds.",
        channel="workspace",
        metadata={"source": "bob-chat-b4f-api"},
        idempotency_key="run-loop-total-limit",
    )

    tool_messages_by_provider_turn = [
        [message for message in messages if message.get("role") == "tool"]
        for messages in provider.messages[1:]
    ]

    assert provider.calls == 5
    assert len(run.actions) == 12
    assert all(len(messages) == expected for messages, expected in zip(tool_messages_by_provider_turn, (3, 6, 9, 12)))
    assert run.metadata["tool_loop"]["executed_tool_calls"] == 12
    assert run.metadata["tool_loop"]["max_total_tool_calls"] == 12
    assert run.metadata["tool_loop"]["limit_reached"] is True


@pytest.mark.asyncio
async def test_runtime_degrades_cleanly_when_provider_fails_before_tools():
    repo = InMemoryAgentRuntimeRepository()
    provider = FailingRuntimeProvider(fail_on_call=1)
    use_cases = AgentRuntimeUseCases(
        repo=repo,
        runtime_provider=provider,
        tool_registry=LocalRuntimeToolRegistry(),
    )
    context = InternalContext(
        tenant_id="tenant-croo-local",
        user_id="user-provider-failure",
        trace_id="1" * 32,
        permissions=("bob_chat.use", "agent.run.create"),
        roles=("admin",),
    )

    run = await use_cases.create_run(
        context=context,
        session_id="session-provider-failure",
        input_message_id="msg-provider-failure",
        prompt="Reponds avec Fireworks.",
        channel="workspace",
        metadata={"source": "bob-chat-b4f-api"},
        idempotency_key="run-provider-failure",
    )

    assert run.status == "completed"
    assert run.mode == "provider_degraded"
    assert run.metadata["provider"] == "runtime_provider"
    assert run.metadata["runtime"]["provider_error"] == "RuntimeError"
    assert run.metadata["tool_loop"]["executed_tool_calls"] == 0
    assert "fournisseur LLM" in run.assistant_content
    assert "should-not-leak" not in run.assistant_content


@pytest.mark.asyncio
async def test_runtime_preserves_tool_results_when_provider_fails_after_tool_call():
    repo = InMemoryAgentRuntimeRepository()
    provider = FailingRuntimeProvider(
        fail_on_call=2,
        before_failure=RuntimeModelResult(
            content="",
            provider="fireworks",
            model="accounts/fireworks/models/kimi-k2p7-code",
            mode="provider_fireworks",
            tool_calls=[
                RuntimeToolCall(
                    id="call-runtime-status-before-failure",
                    name="bob_runtime_status",
                    arguments={"include_tools": False},
                )
            ],
        ),
    )
    use_cases = AgentRuntimeUseCases(
        repo=repo,
        runtime_provider=provider,
        tool_registry=LocalRuntimeToolRegistry(),
    )
    context = InternalContext(
        tenant_id="tenant-croo-local",
        user_id="user-provider-failure-after-tool",
        trace_id="2" * 32,
        permissions=("bob_chat.use", "agent.run.create"),
        roles=("admin",),
    )

    run = await use_cases.create_run(
        context=context,
        session_id="session-provider-failure-after-tool",
        input_message_id="msg-provider-failure-after-tool",
        prompt="Verifie le runtime puis reponds.",
        channel="workspace",
        metadata={"source": "bob-chat-b4f-api"},
        idempotency_key="run-provider-failure-after-tool",
    )

    assert run.mode == "provider_degraded"
    assert [action["tool"] for action in run.actions] == ["bob_runtime_status"]
    assert run.metadata["tool_loop"]["executed_tool_calls"] == 1
    assert run.metadata["runtime"]["provider_error"] == "RuntimeError"
    assert "should-not-leak" not in run.assistant_content


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
            "private": [
                {
                    "id": "mem-1",
                    "title": "Style",
                    "memory_type": "preference",
                    "summary": "Bob doit repondre en francais clair.",
                }
            ],
            "organization": [
                {
                    "id": "org-1",
                    "title": "Procedure",
                    "memory_type": "procedure",
                    "summary": "Factory passe par les queues de validation.",
                }
            ],
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
    mcp_gateway = await registry.execute(
        call=RuntimeToolCall(
            id="call-mcp",
            name="bob_mcp_gateway",
            arguments={"operation": "describe_family", "family": "factory", "risk": "read"},
        ),
        context=context,
        metadata=metadata,
    )
    mcp_write = await registry.execute(
        call=RuntimeToolCall(
            id="call-mcp-write",
            name="bob_mcp_gateway",
            arguments={
                "operation": "execute_capability",
                "family": "factory",
                "capability": "review.write",
                "risk": "write",
            },
        ),
        context=context,
        metadata=metadata,
    )
    mcp_list = await registry.execute(
        call=RuntimeToolCall(
            id="call-mcp-list",
            name="bob_mcp_gateway",
            arguments={"operation": "list_families", "risk": "read"},
        ),
        context=context,
        metadata=metadata,
    )
    memory_status = await registry.execute(
        call=RuntimeToolCall(
            id="call-memory-status",
            name="bob_mcp_gateway",
            arguments={
                "operation": "execute_capability",
                "family": "assistant-memory",
                "capability": "assistant-memory.status",
            },
        ),
        context=context,
        metadata=metadata,
    )
    memory_search = await registry.execute(
        call=RuntimeToolCall(
            id="call-memory-search",
            name="bob_mcp_gateway",
            arguments={
                "operation": "execute_capability",
                "family": "assistant-memory",
                "capability": "assistant-memory.search",
                "query": "Factory",
                "limit": 2,
            },
        ),
        context=context,
        metadata=metadata,
    )
    memory_readback = await registry.execute(
        call=RuntimeToolCall(
            id="call-memory-readback",
            name="bob_mcp_gateway",
            arguments={
                "operation": "execute_capability",
                "family": "assistant-memory",
                "capability": "assistant-memory.readback",
                "limit": 1,
            },
        ),
        context=context,
        metadata=metadata,
    )
    memory_write = await registry.execute(
        call=RuntimeToolCall(
            id="call-memory-write",
            name="bob_mcp_gateway",
            arguments={
                "operation": "execute_capability",
                "family": "assistant-memory",
                "capability": "assistant-memory.record-memory",
            },
        ),
        context=context,
        metadata=metadata,
    )
    support_status = await registry.execute(
        call=RuntimeToolCall(
            id="call-support-status",
            name="bob_mcp_gateway",
            arguments={
                "operation": "execute_capability",
                "family": "support-memory",
                "capability": "support-memory.status",
            },
        ),
        context=context,
        metadata=metadata,
    )
    support_search = await registry.execute(
        call=RuntimeToolCall(
            id="call-support-search",
            name="bob_mcp_gateway",
            arguments={
                "operation": "execute_capability",
                "family": "support-memory",
                "capability": "support-memory.search",
                "query": "validation",
                "limit": 2,
            },
        ),
        context=context,
        metadata=metadata,
    )
    support_playbook = await registry.execute(
        call=RuntimeToolCall(
            id="call-support-playbook",
            name="bob_mcp_gateway",
            arguments={
                "operation": "execute_capability",
                "family": "support-memory",
                "capability": "support-memory.playbook",
                "query": "Factory",
            },
        ),
        context=context,
        metadata=metadata,
    )
    support_write = await registry.execute(
        call=RuntimeToolCall(
            id="call-support-write",
            name="bob_mcp_gateway",
            arguments={
                "operation": "execute_capability",
                "family": "support-memory",
                "capability": "support-memory.propose-training",
            },
        ),
        context=context,
        metadata=metadata,
    )

    assert tools[0]["function"]["name"] == "bob_runtime_status"
    assert {tool["function"]["name"] for tool in tools} == {
        "bob_runtime_status",
        "bob_memory_context_summary",
        "bob_mcp_gateway",
    }
    assert runtime_status.status == "completed"
    assert "available_tool_families" not in runtime_status.content
    assert memory_summary.status == "completed"
    assert "mem-1" in memory_summary.content
    assert mcp_gateway.status == "completed"
    assert "factory-supabase" in mcp_gateway.content
    assert "requests-queues.md" in mcp_gateway.content
    assert mcp_list.status == "completed"
    assert "slack.draft-send" in mcp_list.content
    assert mcp_write.status == "requires_confirmation"
    assert "write_or_destructive_mcp_action_requires_explicit_confirmation" in mcp_write.content
    assert memory_status.status == "completed"
    assert "\"private_count\": 1" in memory_status.content
    assert memory_search.status == "completed"
    assert "Factory passe par les queues" in memory_search.content
    assert memory_readback.status == "completed"
    assert "mem-1" in memory_readback.content
    assert memory_write.status == "requires_confirmation"
    assert memory_write.metadata["risk"] == "write-requested"
    assert "write_or_destructive_mcp_action_requires_explicit_confirmation" in memory_write.content
    assert support_status.status == "completed"
    assert "\"organization_count\": 1" in support_status.content
    assert support_search.status == "completed"
    assert "Factory passe par les queues" in support_search.content
    assert support_playbook.status == "completed"
    assert "\"playbook_count\": 1" in support_status.content
    assert support_write.status == "requires_confirmation"
    assert support_write.metadata["risk"] == "draft"
    assert rejected.status == "rejected"


@pytest.mark.asyncio
async def test_local_registry_filters_tools_by_selected_agent_catalog():
    registry = LocalRuntimeToolRegistry()
    context = InternalContext(
        tenant_id="tenant-croo-local",
        user_id="user-alex-local",
        trace_id="e" * 32,
        permissions=("bob_chat.use",),
        roles=("admin",),
    )

    memory_only = registry.list_tools(
        prompt="Resume la memoire",
        context=context,
        metadata={
            "runtime_catalog": {
                "tools": [{"id": "tool-memory-summary", "name": "bob_memory_context_summary", "family": "memory"}],
            },
        },
    )
    factory_only = registry.list_tools(
        prompt="Liste Factory",
        context=context,
        metadata={
            "runtime_catalog": {
                "tools": [{"id": "tool-cde-factory-read", "name": "factory.requests-queues", "family": "factory"}],
            },
        },
    )
    unmapped = registry.list_tools(
        prompt="Teste un outil non branche",
        context=context,
        metadata={
            "runtime_catalog": {
                "tools": [{"id": "tool-custom-unmapped", "name": "custom_unmapped", "family": "custom"}],
            },
        },
    )
    rejected_ungated = await registry.execute(
        call=RuntimeToolCall(
            id="call-runtime-status-ungated",
            name="bob_runtime_status",
            arguments={"include_tools": True},
        ),
        context=context,
        metadata={
            "runtime_catalog": {
                "tools": [{"id": "tool-cde-factory-read", "name": "factory.requests-queues", "family": "factory"}],
            },
        },
    )

    assert {tool["function"]["name"] for tool in memory_only} == {"bob_memory_context_summary"}
    assert {tool["function"]["name"] for tool in factory_only} == {"bob_mcp_gateway"}
    assert unmapped == []
    assert rejected_ungated.status == "rejected"
    assert "tool_not_allowed_for_selected_agent" in rejected_ungated.content


@pytest.mark.asyncio
async def test_mcp_gateway_executes_factory_read_adapter_and_degrades_cleanly():
    class FakeFactoryAdapter:
        def list_queue_by_project(self, **kwargs):
            return {
                "source": "Factory Supabase",
                "operation": "list_queue_by_project",
                "status": kwargs["status"],
                "total_projects": 1,
                "projects": [{"project_id": "project-1", "project_name": "CDE", "request_count": 2}],
            }

        def list_requests(self, **kwargs):
            return {
                "source": "Factory Supabase",
                "operation": "list_requests",
                "status": kwargs["status"],
                "total_matching": 1,
                "requests": [{"request_id": "request-1", "title": "Installer Bob MCP"}],
            }

        def get_request(self, **kwargs):
            return {
                "source": "Factory Supabase",
                "operation": "get_request",
                "request": {"request_id": kwargs["request_id"], "title": "Installer Bob MCP"},
            }

    class MissingFactoryAdapter(FakeFactoryAdapter):
        def list_queue_by_project(self, **kwargs):
            raise FactorySupabaseAdapterError("factory_supabase_db_url_missing")

    context = InternalContext(
        tenant_id="tenant-croo-local",
        user_id="user-alex-local",
        trace_id="f" * 32,
        permissions=("bob_chat.use", "agent.run.create"),
        roles=("admin",),
    )
    registry = LocalRuntimeToolRegistry(factory_adapter=FakeFactoryAdapter())
    queue = await registry.execute(
        call=RuntimeToolCall(
            id="call-factory-read",
            name="bob_mcp_gateway",
            arguments={
                "operation": "execute_capability",
                "family": "factory",
                "capability": "requests-queues.list_queue_by_project",
                "status": "NEW",
                "risk": "read",
            },
        ),
        context=context,
        metadata={},
    )
    portable_queue = await registry.execute(
        call=RuntimeToolCall(
            id="call-factory-portable-read",
            name="bob_mcp_gateway",
            arguments={
                "operation": "execute_capability",
                "family": "factory",
                "capability": "factory.requests-queues",
                "status": "NEW",
                "risk": "read",
            },
        ),
        context=context,
        metadata={},
    )
    request = await registry.execute(
        call=RuntimeToolCall(
            id="call-factory-get",
            name="bob_mcp_gateway",
            arguments={
                "operation": "execute_capability",
                "family": "factory",
                "capability": "requests-queues.get_request",
                "request_id": "request-1",
                "risk": "read",
            },
        ),
        context=context,
        metadata={},
    )
    degraded = await LocalRuntimeToolRegistry(factory_adapter=MissingFactoryAdapter()).execute(
        call=RuntimeToolCall(
            id="call-factory-missing",
            name="bob_mcp_gateway",
            arguments={
                "operation": "execute_capability",
                "family": "factory",
                "capability": "requests-queues.list_queue_by_project",
                "status": "NEW",
                "risk": "read",
            },
        ),
        context=context,
        metadata={},
    )

    assert queue.status == "completed"
    assert queue.metadata["capability"] == "requests-queues.list_queue_by_project"
    assert "project-1" in queue.content
    assert "external_connector_bound" in queue.content
    assert portable_queue.status == "completed"
    assert portable_queue.metadata["capability"] == "requests-queues.list_queue_by_project"
    assert request.status == "completed"
    assert "Installer Bob MCP" in request.content
    assert degraded.status == "degraded"
    assert "factory_supabase_db_url_missing" in degraded.content


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


def test_factory_supabase_adapter_builds_read_queries_and_errors(monkeypatch):
    class FakeCursor:
        def __init__(self):
            self.last_query = ""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params):
            self.last_query = query
            self.params = params

        def fetchone(self):
            if "COUNT(DISTINCT" in self.last_query:
                return {"total_projects": 1, "total_requests": 2}
            if "COUNT(*)" in self.last_query:
                return {"total_matching": 1}
            if "WHERE r.id" in self.last_query:
                return {"request_id": self.params["request_id"], "title": "Installer Bob MCP"}
            return {}

        def fetchall(self):
            if "project_rank = 1" in self.last_query:
                return [
                    {
                        "project_id": "project-1",
                        "project_name": "CDE",
                        "request_count": 2,
                        "oldest_request_id": "request-1",
                    }
                ]
            return [{"request_id": "request-1", "title": "Installer Bob MCP", "status": "NEW"}]

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

    calls = []

    def fake_connect(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeConnection()

    monkeypatch.setattr("app.infrastructure.tools.factory_supabase_adapter.psycopg.connect", fake_connect)
    adapter = FactorySupabaseAdapter(db_url="postgresql://factory.example/db", connect_timeout=3)

    queue = adapter.list_queue_by_project(status="new", limit=500, offset=-10)
    requests = adapter.list_requests(project_id="", query="bob", status="new", limit=250, offset=0)
    request = adapter.get_request(request_id="request-1")

    assert queue["status"] == "NEW"
    assert queue["limit"] == 100
    assert queue["offset"] == 0
    assert queue["projects"][0]["project_id"] == "project-1"
    assert requests["total_matching"] == 1
    assert requests["requests"][0]["title"] == "Installer Bob MCP"
    assert request["request"]["request_id"] == "request-1"
    assert calls[0][0] == ("postgresql://factory.example/db",)
    assert calls[0][1]["connect_timeout"] == 3

    with pytest.raises(FactorySupabaseAdapterError) as missing_url:
        FactorySupabaseAdapter(db_url="").list_queue_by_project()
    assert missing_url.value.code == "factory_supabase_db_url_missing"

    with pytest.raises(FactorySupabaseAdapterError) as missing_id:
        adapter.get_request(request_id="")
    assert missing_id.value.code == "request_id_required"


def test_factory_supabase_adapter_from_env_and_connection_failure(monkeypatch):
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://fallback.example/db")
    monkeypatch.setenv("FACTORY_SUPABASE_CONNECT_TIMEOUT_SECONDS", "bad")
    adapter = FactorySupabaseAdapter.from_env()
    assert adapter.db_url == "postgresql://fallback.example/db"
    assert adapter.connect_timeout == 10

    def broken_connect(*args, **kwargs):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr("app.infrastructure.tools.factory_supabase_adapter.psycopg.connect", broken_connect)
    with pytest.raises(FactorySupabaseAdapterError) as error:
        adapter.list_requests()
    assert error.value.code == "factory_supabase_connection_failed"


@pytest.mark.asyncio
async def test_local_provider_honors_explicit_factory_queue_capability():
    provider = LocalRuntimeProvider()
    result = await provider.complete(
        messages=[
            {
                "role": "user",
                "content": (
                    "Exécute bob_mcp_gateway avec la capability Factory "
                    "requests-queues.list_queue_by_project en lecture, statut NEW."
                ),
            }
        ],
        tools=[{"type": "function", "function": {"name": "bob_mcp_gateway"}}],
        trace_id="a" * 32,
    )

    assert result.tool_calls
    assert result.tool_calls[0].arguments["operation"] == "execute_capability"
    assert result.tool_calls[0].arguments["capability"] == "requests-queues.list_queue_by_project"
    assert result.tool_calls[0].arguments["status"] == "NEW"


@pytest.mark.asyncio
async def test_local_provider_routes_private_memory_to_mcp_gateway():
    provider = LocalRuntimeProvider()
    result = await provider.complete(
        messages=[
            {
                "role": "user",
                "content": "Cherche dans ma mémoire privée la préférence de langue pour Bob.",
            }
        ],
        tools=[{"type": "function", "function": {"name": "bob_mcp_gateway"}}],
        trace_id="a" * 32,
    )

    assert result.tool_calls
    call = result.tool_calls[0]
    assert call.name == "bob_mcp_gateway"
    assert call.arguments["operation"] == "execute_capability"
    assert call.arguments["family"] == "assistant-memory"
    assert call.arguments["capability"] == "assistant-memory.search"
    assert call.arguments["risk"] == "read"


@pytest.mark.asyncio
async def test_local_provider_does_not_route_memory_without_mcp_gateway_tool():
    provider = LocalRuntimeProvider()
    result = await provider.complete(
        messages=[
            {
                "role": "user",
                "content": "Cherche dans ma mémoire privée la préférence de langue pour Bob.",
            }
        ],
        tools=[{"type": "function", "function": {"name": "bob_runtime_status"}}],
        trace_id="a" * 32,
    )

    assert result.tool_calls
    assert result.tool_calls[0].name == "bob_runtime_status"


@pytest.mark.asyncio
async def test_local_provider_routes_support_playbook_to_mcp_gateway():
    provider = LocalRuntimeProvider()
    result = await provider.complete(
        messages=[
            {
                "role": "user",
                "content": "Va lire le playbook support dans la mémoire d'organisation pour Factory.",
            }
        ],
        tools=[{"type": "function", "function": {"name": "bob_mcp_gateway"}}],
        trace_id="a" * 32,
    )

    assert result.tool_calls
    call = result.tool_calls[0]
    assert call.name == "bob_mcp_gateway"
    assert call.arguments["operation"] == "execute_capability"
    assert call.arguments["family"] == "support-memory"
    assert call.arguments["capability"] == "support-memory.playbook"
    assert call.arguments["risk"] == "read"


@pytest.mark.asyncio
async def test_local_provider_routes_organization_memory_search_to_support_memory():
    provider = LocalRuntimeProvider()
    result = await provider.complete(
        messages=[
            {
                "role": "user",
                "content": "Cherche dans la mémoire organisation la règle Factory.",
            }
        ],
        tools=[{"type": "function", "function": {"name": "bob_mcp_gateway"}}],
        trace_id="a" * 32,
    )

    assert result.tool_calls
    call = result.tool_calls[0]
    assert call.name == "bob_mcp_gateway"
    assert call.arguments["family"] == "support-memory"
    assert call.arguments["capability"] == "support-memory.search"
    assert call.arguments["risk"] == "read"


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
