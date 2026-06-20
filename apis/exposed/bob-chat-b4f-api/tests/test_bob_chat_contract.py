from fastapi.testclient import TestClient
import httpx
import pytest

import main
from app.application.services.idempotency import InMemoryIdempotencyStore
from app.application.use_cases.bob_chat_use_cases import BobChatUseCases
from app.domain import (
    BobChatIntegrationError,
    BobChatNotFoundError,
    BobChatSecurityContext,
)
from app.infrastructure.clients.agent_memory_client import AgentMemoryBackendClient
from app.infrastructure.clients.agent_runtime_client import AgentRuntimeBackendClient
from app.infrastructure.clients.bob_cloud_identity import BobCloudIdentityProvider
from app.infrastructure.clients.conversation_client import ConversationBackendClient
from app.presentation import deps
from app.presentation.routes import bob_chat_routes
from shared.infrastructure import InternalSessionContextSigner
from shared.services import BobCloudModeError, BobCloudResponseError


class FakeIdentityProvider:
    def __init__(self):
        self.status_code = 200
        self.detail = None
        self.calls = []

    async def resolve(self, *, forward_headers=None, trace_id=""):
        self.calls.append({"headers": dict(forward_headers or {}), "trace_id": trace_id})
        if self.status_code != 200:
            raise BobChatIntegrationError(
                "identity_rejected",
                status_code=self.status_code,
                detail=self.detail or {"code": "identity_rejected"},
            )
        return BobChatSecurityContext(
            tenant_id="tenant-croo-local",
            user_id="user-alex-local",
            session_id="sess-bob-cloud-stub",
            trace_id=trace_id,
            internal_session_context="signed-internal-context",
        )


class FakeConversationClient:
    def __init__(self):
        self.sessions = {}
        self.messages = {}
        self.calls = []

    async def create_session(self, *, draft, security_context):
        session = {
            "id": "chat-local-1",
            "title": draft.title,
            "channel": draft.channel,
            "status": "active",
            "turn_count": 0,
            "created_at": "2026-06-19T00:00:00Z",
            "updated_at": "2026-06-19T00:00:00Z",
            "mission": draft.mission,
            "client_context": draft.client_context,
        }
        self.sessions[session["id"]] = session
        self.calls.append(("create_session", security_context.internal_session_context))
        return session

    async def list_sessions(self, *, security_context):
        self.calls.append(("list_sessions", security_context.internal_session_context))
        return {"items": list(self.sessions.values())}

    async def get_session(self, *, session_id, security_context):
        self.calls.append(("get_session", session_id, security_context.internal_session_context))
        if session_id not in self.sessions:
            raise BobChatNotFoundError(
                "session_not_found",
                status_code=404,
                detail={"code": "session_not_found", "session_id": session_id},
            )
        return self.sessions[session_id]

    async def delete_session(self, *, session_id, security_context):
        self.calls.append(("delete_session", session_id, security_context.internal_session_context))
        if session_id not in self.sessions:
            raise BobChatNotFoundError(
                "session_not_found",
                status_code=404,
                detail={"code": "session_not_found", "session_id": session_id},
            )
        del self.sessions[session_id]

    async def add_message(
        self,
        *,
        session_id,
        role,
        content,
        security_context,
        idempotency_key,
        metadata=None,
    ):
        self.calls.append(("add_message", session_id, role, idempotency_key))
        message = {
            "id": f"msg-{len(self.messages) + 1}",
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": "2026-06-19T00:00:00Z",
            "metadata": dict(metadata or {}),
        }
        self.messages[message["id"]] = message
        if role == "user":
            self.sessions[session_id]["turn_count"] += 1
        return message


class FakeRuntimeClient:
    def __init__(self):
        self.calls = []

    async def create_run(
        self,
        *,
        session_id,
        input_message_id,
        prompt,
        channel,
        metadata,
        security_context,
        idempotency_key,
    ):
        self.calls.append(
            (
                "create_run",
                session_id,
                input_message_id,
                prompt,
                channel,
                metadata,
                idempotency_key,
                security_context.internal_session_context,
            )
        )
        return {
            "id": "run-local-1",
            "session_id": session_id,
            "input_message_id": input_message_id,
            "status": "completed",
            "mode": "local_runtime",
            "trace_id": security_context.trace_id,
            "assistant_content": f"Runtime Bob: {prompt}",
            "narration_steps": [{"label": "demande_recue", "status": "complete"}],
            "actions": [],
            "artifacts": [],
        }


class FakeMemoryClient:
    def __init__(self):
        self.calls = []

    async def build_context(self, *, query, security_context):
        self.calls.append(("build_context", query, security_context.internal_session_context))
        return {
            "private": [
                {
                    "id": "mem-1",
                    "memory_type": "preference",
                    "title": "Style",
                    "content": "Repondre en francais.",
                }
            ],
            "organization": [],
            "degraded": [],
            "source": "agent-memory-backend-api",
        }


@pytest.fixture()
def fake_identity():
    return FakeIdentityProvider()


@pytest.fixture()
def fake_conversation():
    return FakeConversationClient()


@pytest.fixture()
def fake_runtime():
    return FakeRuntimeClient()


@pytest.fixture()
def fake_memory():
    return FakeMemoryClient()


@pytest.fixture()
def client(fake_identity, fake_conversation, fake_runtime, fake_memory):
    idempotency_store = InMemoryIdempotencyStore()
    use_cases = BobChatUseCases(
        identity_provider=fake_identity,
        conversation_client=fake_conversation,
        runtime_client=fake_runtime,
        memory_client=fake_memory,
        idempotency_store=idempotency_store,
    )
    main.app.dependency_overrides[bob_chat_routes.get_bob_chat_use_cases] = lambda: use_cases
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()
    idempotency_store.clear()


def test_monitoring_endpoints(client):
    for path in ["/health", "/readiness", "/liveness", "/startup", "/metrics"]:
        response = client.get(path)
        assert response.status_code == 200
    assert "dependencies" in client.get("/health").json()
    assert "cde_api_info" in client.get("/metrics").text


def test_create_message_requires_idempotency_key(client):
    response = client.post("/api/bob-chat/v1/messages", json={"message": "Bonjour Bob"})

    assert response.status_code == 422


def test_create_message_validates_identity_and_delegates_conversation_runtime(
    client,
    fake_identity,
    fake_conversation,
    fake_runtime,
    fake_memory,
):
    response = client.post(
        "/api/bob-chat/v1/messages",
        json={
            "message": "Montre mes suivis prioritaires",
            "agent_id": "agent-bob-orchestrator",
            "client_context": {"route": "/opportunities"},
        },
        headers={"Idempotency-Key": "msg-1", "Cookie": "bob_cloud_session=abc", "X-Trace-Id": "a" * 32},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"]["role"] == "assistant"
    assert payload["input_message"]["role"] == "user"
    assert payload["message"]["content"] == "Runtime Bob: Montre mes suivis prioritaires"
    assert payload["session"]["status"] == "active"
    assert payload["session"]["turn_count"] == 1
    assert payload["run"]["id"] == "run-local-1"
    assert payload["run"]["status"] == "completed"
    assert payload["run"]["mode"] == "local_runtime"
    assert payload["run"]["trace_id"] == "a" * 32
    assert payload["narration_steps"] == [
        {
            "label": "demande_recue",
            "kind": "validate",
            "status": "complete",
            "safe_to_show": True,
        }
    ]
    assert "internal_session_context" not in payload
    assert fake_identity.calls[0]["headers"]["cookie"] == "bob_cloud_session=abc"
    assert fake_conversation.calls[0] == ("create_session", "signed-internal-context")
    assert fake_conversation.calls[1][0] == "add_message"
    assert fake_memory.calls[0] == ("build_context", "Montre mes suivis prioritaires", "signed-internal-context")
    assert fake_runtime.calls[0][0] == "create_run"
    assert fake_runtime.calls[0][2] == "msg-1"
    assert fake_runtime.calls[0][5]["agent_id"] == "agent-bob-orchestrator"
    assert fake_runtime.calls[0][5]["memory_context"]["private"][0]["id"] == "mem-1"
    assert fake_runtime.calls[0][6] == "msg-1:run"


def test_create_message_maps_runtime_narration_to_public_frontend_contract(
    client,
    fake_runtime,
):
    async def create_run_with_visible_steps(**kwargs):
        return {
            "id": "run-local-steps",
            "session_id": kwargs["session_id"],
            "input_message_id": kwargs["input_message_id"],
            "status": "completed",
            "mode": "provider_fireworks",
            "trace_id": kwargs["security_context"].trace_id,
            "assistant_content": "Bob confirme son runtime.",
            "narration_steps": [
                {"label": "provider_runtime", "status": "complete", "visible": True},
                {"label": "outil_bob_runtime_status", "status": "completed", "visible": True},
                {"label": "secret_interne", "status": "complete", "visible": False},
            ],
            "actions": [],
            "artifacts": [],
        }

    fake_runtime.create_run = create_run_with_visible_steps

    response = client.post(
        "/api/bob-chat/v1/messages",
        json={"message": "Confirme ton runtime"},
        headers={"Idempotency-Key": "msg-narration-contract"},
    )

    assert response.status_code == 200
    assert response.json()["narration_steps"] == [
        {
            "label": "provider_runtime",
            "kind": "validate",
            "status": "complete",
            "safe_to_show": True,
        },
        {
            "label": "outil_bob_runtime_status",
            "kind": "lookup",
            "status": "completed",
            "safe_to_show": True,
        },
        {
            "label": "secret_interne",
            "kind": "lookup",
            "status": "complete",
            "safe_to_show": False,
        },
    ]


def test_gateway_rewritten_internal_paths_are_supported(
    client,
    fake_conversation,
):
    created = client.post(
        "/messages",
        json={"message": "Bonjour depuis le gateway"},
        headers={"Idempotency-Key": "internal-msg-1"},
    )
    listed = client.get("/sessions")

    assert created.status_code == 200
    assert created.json()["session"]["id"]
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == created.json()["session"]["id"]
    assert any(call[0] == "create_session" for call in fake_conversation.calls)


def test_idempotency_replays_same_response_for_same_payload(
    client,
    fake_conversation,
    fake_runtime,
    fake_memory,
):
    body = {"message": "Bonjour Bob"}
    headers = {"Idempotency-Key": "same-key"}

    first = client.post("/api/bob-chat/v1/messages", json=body, headers=headers)
    second = client.post("/api/bob-chat/v1/messages", json=body, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    add_message_calls = [call for call in fake_conversation.calls if call[0] == "add_message"]
    assert len(add_message_calls) == 2
    assert len(fake_runtime.calls) == 1
    assert len(fake_memory.calls) == 1


def test_idempotency_conflict_for_different_payload(client):
    headers = {"Idempotency-Key": "conflict-key"}
    first = client.post("/api/bob-chat/v1/messages", json={"message": "Premier"}, headers=headers)
    second = client.post("/api/bob-chat/v1/messages", json={"message": "Deuxieme"}, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == {"code": "idempotency_conflict"}


def test_create_message_refuses_missing_session(client, fake_identity):
    fake_identity.status_code = 401
    fake_identity.detail = {"code": "not_authenticated"}

    response = client.post(
        "/api/bob-chat/v1/messages",
        json={"message": "Bonjour"},
        headers={"Idempotency-Key": "msg-1"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == {"code": "not_authenticated"}


def test_create_message_refuses_missing_entitlement(client, fake_identity):
    fake_identity.status_code = 403
    fake_identity.detail = {"code": "capability_denied"}

    response = client.post(
        "/api/bob-chat/v1/messages",
        json={"message": "Bonjour"},
        headers={"Idempotency-Key": "msg-1"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == {"code": "capability_denied"}


def test_sessions_routes_delegate_to_conversation_backend(client, fake_conversation):
    created = client.post(
        "/api/bob-chat/v1/messages",
        json={"message": "Bonjour Bob"},
        headers={"Idempotency-Key": "session-seed"},
    )
    session_id = created.json()["session"]["id"]

    listed = client.get("/api/bob-chat/v1/sessions")
    fetched = client.get(f"/api/bob-chat/v1/sessions/{session_id}")
    deleted = client.delete(f"/api/bob-chat/v1/sessions/{session_id}")
    missing = client.get(f"/api/bob-chat/v1/sessions/{session_id}")

    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == session_id
    assert fetched.status_code == 200
    assert deleted.status_code == 204
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "session_not_found"


def test_bob_cloud_configuration_error_is_mapped():
    def broken_factory():
        raise BobCloudModeError("BOB_CLOUD_API_URL is required when BOB_CLOUD_MODE=real")

    original_factory = deps.create_bob_cloud_client_from_env
    deps.create_bob_cloud_client_from_env = broken_factory
    try:
        response = deps.get_bob_cloud_client()
    except Exception as exc:
        mapped = exc
    finally:
        deps.create_bob_cloud_client_from_env = original_factory

    assert mapped.status_code == 503
    assert mapped.detail["code"] == "bob_cloud_unconfigured"


@pytest.mark.asyncio
async def test_bob_cloud_identity_provider_issues_internal_context():
    class BobCloudClient:
        async def get_session(self, forward_headers=None):
            return {
                "authenticated": True,
                "session_id": "sess-bob-cloud-stub",
                "user": {"id": "user-alex-local"},
                "tenant": {"id": "tenant-croo-local"},
                "permissions": ["bob_chat.use"],
                "platform_roles": ["admin"],
            }

        async def check_capability(self, capability, forward_headers=None):
            return {"capability": capability, "status": "enabled"}

    signer = InternalSessionContextSigner("test-internal-secret", kid="test-kid")
    provider = BobCloudIdentityProvider(bob_cloud_client=BobCloudClient(), signer=signer)

    context = await provider.resolve(forward_headers={"cookie": "abc"}, trace_id="c" * 32)

    assert context.tenant_id == "tenant-croo-local"
    assert context.user_id == "user-alex-local"
    assert signer.validate(context.internal_session_context).trace_id == "c" * 32


@pytest.mark.asyncio
async def test_bob_cloud_identity_provider_maps_auth_and_capability_errors():
    class AnonymousBobCloudClient:
        async def get_session(self, forward_headers=None):
            return {"authenticated": False}

        async def check_capability(self, capability, forward_headers=None):
            return {"capability": capability, "status": "enabled"}

    class DeniedBobCloudClient:
        async def get_session(self, forward_headers=None):
            return {
                "authenticated": True,
                "session_id": "sess-bob-cloud-stub",
                "user": {"id": "user-alex-local"},
                "tenant": {"id": "tenant-croo-local"},
            }

        async def check_capability(self, capability, forward_headers=None):
            return {"capability": capability, "status": "denied", "reason_code": "license_missing"}

    signer = InternalSessionContextSigner("test-internal-secret", kid="test-kid")
    anonymous = BobCloudIdentityProvider(bob_cloud_client=AnonymousBobCloudClient(), signer=signer)
    denied = BobCloudIdentityProvider(bob_cloud_client=DeniedBobCloudClient(), signer=signer)

    with pytest.raises(BobChatIntegrationError) as not_authenticated:
        await anonymous.resolve(forward_headers={}, trace_id="d" * 32)
    with pytest.raises(BobChatIntegrationError) as license_denied:
        await denied.resolve(forward_headers={}, trace_id="d" * 32)

    assert not_authenticated.value.status_code == 401
    assert license_denied.value.status_code == 403
    assert license_denied.value.detail == {"code": "license_missing"}


@pytest.mark.asyncio
async def test_bob_cloud_identity_provider_maps_transport_errors():
    class RejectedBobCloudClient:
        async def get_session(self, forward_headers=None):
            raise BobCloudResponseError(
                status_code=403,
                detail={"code": "license_missing"},
                path="/api/auth/v1/session",
                method="GET",
            )

        async def check_capability(self, capability, forward_headers=None):
            return {"capability": capability, "status": "enabled"}

    signer = InternalSessionContextSigner("test-internal-secret", kid="test-kid")
    provider = BobCloudIdentityProvider(bob_cloud_client=RejectedBobCloudClient(), signer=signer)

    with pytest.raises(BobChatIntegrationError) as mapped:
        await provider.resolve(forward_headers={}, trace_id="e" * 32)

    assert mapped.value.status_code == 403
    assert mapped.value.detail == {"code": "license_missing"}


@pytest.mark.asyncio
async def test_conversation_backend_client_delegates_signed_calls():
    class HTTPClient:
        def __init__(self):
            self.calls = []

        async def post(self, path, json=None, headers=None):
            self.calls.append(("post", path, json, headers))
            if path.endswith("/messages"):
                return httpx.Response(
                    201,
                    json={
                        "id": "msg-1",
                        "session_id": "chat-1",
                        "role": json["role"],
                        "content": json["content"],
                    },
                )
            return httpx.Response(201, json={"id": "chat-1", "title": json["title"]})

        async def get(self, path, headers=None):
            self.calls.append(("get", path, None, headers))
            if path.endswith("/sessions"):
                return httpx.Response(200, json={"items": []})
            return httpx.Response(200, json={"id": "chat-1", "title": "Bonjour"})

        async def delete(self, path, headers=None):
            self.calls.append(("delete", path, None, headers))
            return httpx.Response(204)

    http_client = HTTPClient()
    client_adapter = ConversationBackendClient(client=http_client)
    security_context = BobChatSecurityContext(
        tenant_id="tenant-croo-local",
        user_id="user-alex-local",
        session_id="sess",
        trace_id="f" * 32,
        internal_session_context="signed",
    )
    draft = type("Draft", (), {
        "title": "Bonjour",
        "channel": "workspace",
        "mission": None,
        "client_context": {},
    })()

    created = await client_adapter.create_session(draft=draft, security_context=security_context)
    listed = await client_adapter.list_sessions(security_context=security_context)
    fetched = await client_adapter.get_session(session_id="chat-1", security_context=security_context)
    message = await client_adapter.add_message(
        session_id="chat-1",
        role="user",
        content="Bonjour",
        security_context=security_context,
        idempotency_key="idem-1",
    )
    await client_adapter.delete_session(session_id="chat-1", security_context=security_context)

    assert created["id"] == "chat-1"
    assert listed["items"] == []
    assert fetched["id"] == "chat-1"
    assert message["id"] == "msg-1"
    assert http_client.calls[0][3]["X-Session-Context"] == "signed"
    assert http_client.calls[3][3]["Idempotency-Key"] == "idem-1"


@pytest.mark.asyncio
async def test_conversation_backend_client_maps_not_found_and_unavailable():
    class NotFoundHTTPClient:
        async def get(self, path, headers=None):
            return httpx.Response(404, json={"detail": {"code": "session_not_found"}})

    class UnavailableHTTPClient:
        async def get(self, path, headers=None):
            raise httpx.ConnectError("no route")

    security_context = BobChatSecurityContext(
        tenant_id="tenant-croo-local",
        user_id="user-alex-local",
        session_id="sess",
        trace_id="f" * 32,
        internal_session_context="signed",
    )

    with pytest.raises(BobChatNotFoundError):
        await ConversationBackendClient(client=NotFoundHTTPClient()).get_session(
            session_id="chat-missing",
            security_context=security_context,
        )
    with pytest.raises(BobChatIntegrationError) as unavailable:
        await ConversationBackendClient(client=UnavailableHTTPClient()).get_session(
            session_id="chat-missing",
            security_context=security_context,
        )

    assert unavailable.value.status_code == 503


@pytest.mark.asyncio
async def test_agent_memory_backend_client_builds_private_and_organization_context():
    class HTTPClient:
        def __init__(self):
            self.calls = []

        async def post(self, path, json=None, headers=None):
            self.calls.append(("post", path, json, headers))
            if path.endswith("/organization/search"):
                return httpx.Response(
                    200,
                    json={
                        "scope_type": "organization",
                        "isolation_enforced": True,
                        "results": [
                            {
                                "id": "org-1",
                                "scope_type": "organization",
                                "memory_type": "organization_knowledge",
                                "title": "Procedure",
                                "content": "Procedure equipe",
                                "source_ref": "doc-1",
                                "sensitivity": "internal",
                                "verified_at": "2026-06-19T00:00:00Z",
                            }
                        ],
                    },
                )
            return httpx.Response(
                200,
                json={
                    "scope_type": "private_user",
                    "isolation_enforced": True,
                    "results": [
                        {
                            "id": "mem-1",
                            "scope_type": "private_user",
                            "memory_type": "preference",
                            "title": "Style",
                            "content": "Francais court",
                            "source_ref": "chat-1",
                            "sensitivity": "private_user",
                            "verified_at": "2026-06-19T00:00:00Z",
                        }
                    ],
                },
            )

    http_client = HTTPClient()
    security_context = BobChatSecurityContext(
        tenant_id="tenant-croo-local",
        user_id="user-alex-local",
        session_id="sess",
        trace_id="f" * 32,
        internal_session_context="signed",
    )

    memory_context = await AgentMemoryBackendClient(client=http_client).build_context(
        query="Bonjour",
        security_context=security_context,
    )

    assert memory_context["private"][0]["id"] == "mem-1"
    assert memory_context["organization"][0]["id"] == "org-1"
    assert memory_context["degraded"] == []
    assert http_client.calls[0][1] == "/internal/agent-memory/v1/search"
    assert http_client.calls[1][1] == "/internal/agent-memory/v1/organization/search"
    assert http_client.calls[0][3]["X-Session-Context"] == "signed"


@pytest.mark.asyncio
async def test_agent_memory_backend_client_degrades_without_failing_chat():
    class HTTPClient:
        async def post(self, path, json=None, headers=None):
            if path.endswith("/organization/search"):
                return httpx.Response(403, json={"detail": {"code": "organization_memory_forbidden"}})
            raise httpx.ConnectError("no route")

    security_context = BobChatSecurityContext(
        tenant_id="tenant-croo-local",
        user_id="user-alex-local",
        session_id="sess",
        trace_id="f" * 32,
        internal_session_context="signed",
    )

    memory_context = await AgentMemoryBackendClient(client=HTTPClient()).build_context(
        query="Bonjour",
        security_context=security_context,
    )

    assert memory_context["private"] == []
    assert memory_context["organization"] == []
    assert "organization_memory_forbidden" in memory_context["degraded"]
    assert any(item.startswith("memory_backend_unavailable") for item in memory_context["degraded"])


@pytest.mark.asyncio
async def test_agent_runtime_backend_client_delegates_signed_run_call():
    class HTTPClient:
        def __init__(self):
            self.calls = []

        async def post(self, path, json=None, headers=None):
            self.calls.append(("post", path, json, headers))
            return httpx.Response(
                201,
                json={
                    "id": "run-1",
                    "status": "completed",
                    "mode": "local_runtime",
                    "trace_id": headers["X-Trace-Id"],
                    "assistant_content": "Runtime Bob",
                    "narration_steps": [],
                    "actions": [],
                    "artifacts": [],
                },
            )

    http_client = HTTPClient()
    client_adapter = AgentRuntimeBackendClient(client=http_client)
    security_context = BobChatSecurityContext(
        tenant_id="tenant-croo-local",
        user_id="user-alex-local",
        session_id="sess",
        trace_id="f" * 32,
        internal_session_context="signed",
    )

    run = await client_adapter.create_run(
        session_id="chat-1",
        input_message_id="msg-1",
        prompt="Bonjour",
        channel="workspace",
        metadata={"source": "test"},
        security_context=security_context,
        idempotency_key="idem-run",
    )

    assert run["id"] == "run-1"
    assert http_client.calls[0][1] == "/internal/agent-runtime/v1/runs"
    assert http_client.calls[0][2]["input_message_id"] == "msg-1"
    assert http_client.calls[0][3]["X-Session-Context"] == "signed"
    assert http_client.calls[0][3]["Idempotency-Key"] == "idem-run"


@pytest.mark.asyncio
async def test_agent_runtime_backend_client_maps_errors():
    class RejectedHTTPClient:
        async def post(self, path, json=None, headers=None):
            return httpx.Response(409, json={"detail": {"code": "runtime_rejected"}})

    class UnavailableHTTPClient:
        async def post(self, path, json=None, headers=None):
            raise httpx.ConnectError("no route")

    security_context = BobChatSecurityContext(
        tenant_id="tenant-croo-local",
        user_id="user-alex-local",
        session_id="sess",
        trace_id="f" * 32,
        internal_session_context="signed",
    )

    with pytest.raises(BobChatIntegrationError) as rejected:
        await AgentRuntimeBackendClient(client=RejectedHTTPClient()).create_run(
            session_id="chat-1",
            input_message_id="msg-1",
            prompt="Bonjour",
            channel="workspace",
            metadata={},
            security_context=security_context,
            idempotency_key="idem-run",
        )
    with pytest.raises(BobChatIntegrationError) as unavailable:
        await AgentRuntimeBackendClient(client=UnavailableHTTPClient()).create_run(
            session_id="chat-1",
            input_message_id="msg-1",
            prompt="Bonjour",
            channel="workspace",
            metadata={},
            security_context=security_context,
            idempotency_key="idem-run",
        )

    assert rejected.value.status_code == 409
    assert rejected.value.detail == {"code": "runtime_rejected"}
    assert unavailable.value.status_code == 503


def test_python_package_contract_loads_runtime_components():
    from bob_chat_b4f_api.contract import CONTRACT_VERSION, load_runtime_components

    assert CONTRACT_VERSION == "0.1.0"
    assert len(load_runtime_components()) == 8
