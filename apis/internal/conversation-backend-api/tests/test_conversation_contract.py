from fastapi.testclient import TestClient
import pytest

import main
from app.application.use_cases.conversation_use_cases import ConversationUseCases
from app.infrastructure.persistence.in_memory_conversation_repository import (
    InMemoryConversationRepository,
)
from app.presentation.routes import conversation_routes
from shared.infrastructure import InternalSessionContext, InternalSessionContextSigner


@pytest.fixture()
def conversation_repo():
    return InMemoryConversationRepository()


@pytest.fixture()
def client(conversation_repo):
    use_cases = ConversationUseCases(repo=conversation_repo)
    main.app.dependency_overrides[conversation_routes.get_conversation_use_cases] = lambda: use_cases
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
        trace_id="b" * 32,
        permissions=("bob_chat.use",),
        entitlements=("bob_chat.use",),
        roles=("admin",),
    )
    return {
        "X-Session-Context": signer.issue(context),
        "X-Trace-Id": "b" * 32,
    }


def test_monitoring_endpoints_do_not_require_internal_context(client):
    for path in ["/health", "/readiness", "/liveness", "/startup", "/metrics"]:
        response = client.get(path)
        assert response.status_code == 200


def test_internal_routes_require_signed_context(client):
    response = client.get("/internal/conversation/v1/sessions")

    assert response.status_code == 401


def test_create_session_and_add_messages(client):
    created = client.post(
        "/internal/conversation/v1/sessions",
        json={"title": "Bonjour Bob", "channel": "workspace", "client_context": {"route": "/conversation"}},
        headers=signed_headers(),
    )

    assert created.status_code == 201
    session = created.json()
    assert session["id"].startswith("chat_")
    assert session["turn_count"] == 0

    user_message = client.post(
        f"/internal/conversation/v1/sessions/{session['id']}/messages",
        json={"role": "user", "content": "Montre mes priorites", "metadata": {"source": "test"}},
        headers={**signed_headers(), "Idempotency-Key": "idem-user-1"},
    )
    assistant_message = client.post(
        f"/internal/conversation/v1/sessions/{session['id']}/messages",
        json={"role": "assistant", "content": "Voici le recap.", "metadata": {"source": "test"}},
        headers={**signed_headers(), "Idempotency-Key": "idem-assistant-1"},
    )

    assert user_message.status_code == 201
    assert user_message.json()["role"] == "user"
    assert assistant_message.status_code == 201

    fetched = client.get(
        f"/internal/conversation/v1/sessions/{session['id']}",
        headers=signed_headers(),
    )
    messages = client.get(
        f"/internal/conversation/v1/sessions/{session['id']}/messages",
        headers=signed_headers(),
    )

    assert fetched.status_code == 200
    assert fetched.json()["turn_count"] == 1
    assert messages.status_code == 200
    assert [item["role"] for item in messages.json()["items"]] == ["user", "assistant"]


def test_message_idempotency_replays_existing_message(client):
    created = client.post(
        "/internal/conversation/v1/sessions",
        json={"title": "Idempotence", "channel": "workspace"},
        headers=signed_headers(),
    )
    session_id = created.json()["id"]

    first = client.post(
        f"/internal/conversation/v1/sessions/{session_id}/messages",
        json={"role": "user", "content": "Une fois"},
        headers={**signed_headers(), "Idempotency-Key": "same-message"},
    )
    second = client.post(
        f"/internal/conversation/v1/sessions/{session_id}/messages",
        json={"role": "user", "content": "Payload change mais cle identique"},
        headers={**signed_headers(), "Idempotency-Key": "same-message"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json() == second.json()


def test_session_scope_is_tenant_and_user_bound(client):
    created = client.post(
        "/internal/conversation/v1/sessions",
        json={"title": "Scope", "channel": "workspace"},
        headers=signed_headers(user_id="user-a"),
    )
    session_id = created.json()["id"]

    foreign_user = client.get(
        f"/internal/conversation/v1/sessions/{session_id}",
        headers=signed_headers(user_id="user-b"),
    )
    foreign_tenant = client.get(
        f"/internal/conversation/v1/sessions/{session_id}",
        headers=signed_headers(tenant_id="tenant-other", user_id="user-a"),
    )

    assert foreign_user.status_code == 404
    assert foreign_tenant.status_code == 404


def test_delete_session_hides_it_from_list(client):
    created = client.post(
        "/internal/conversation/v1/sessions",
        json={"title": "Delete", "channel": "workspace"},
        headers=signed_headers(),
    )
    session_id = created.json()["id"]

    deleted = client.delete(
        f"/internal/conversation/v1/sessions/{session_id}",
        headers=signed_headers(),
    )
    listed = client.get("/internal/conversation/v1/sessions", headers=signed_headers())
    missing = client.get(
        f"/internal/conversation/v1/sessions/{session_id}",
        headers=signed_headers(),
    )

    assert deleted.status_code == 204
    assert listed.status_code == 200
    assert listed.json()["items"] == []
    assert missing.status_code == 404


def test_missing_session_errors_are_contractual(client):
    delete_missing = client.delete(
        "/internal/conversation/v1/sessions/chat-missing",
        headers=signed_headers(),
    )
    add_message_missing = client.post(
        "/internal/conversation/v1/sessions/chat-missing/messages",
        json={"role": "user", "content": "Bonjour"},
        headers={**signed_headers(), "Idempotency-Key": "missing-message"},
    )
    list_messages_missing = client.get(
        "/internal/conversation/v1/sessions/chat-missing/messages",
        headers=signed_headers(),
    )

    assert delete_missing.status_code == 404
    assert delete_missing.json()["detail"] == {"code": "session_not_found"}
    assert add_message_missing.status_code == 404
    assert add_message_missing.json()["detail"] == {"code": "session_not_found"}
    assert list_messages_missing.status_code == 404
    assert list_messages_missing.json()["detail"] == {"code": "session_not_found"}


def test_python_package_contract_loads_runtime_components():
    from conversation_backend_api.contract import CONTRACT_VERSION, load_runtime_components

    assert CONTRACT_VERSION == "0.1.0"
    assert len(load_runtime_components()) == 4
