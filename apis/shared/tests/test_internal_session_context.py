import base64
import json
import time

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from shared.infrastructure.internal_session_context import (
    InMemoryReplayStore,
    InternalSessionContext,
    InternalSessionContextError,
    InternalSessionContextMiddleware,
    InternalSessionContextSigner,
)


SECRET = "test-secret-for-internal-session-context-32"


def _signer(replay_store=None):
    return InternalSessionContextSigner(
        SECRET,
        kid="internal-session-test",
        replay_store=replay_store,
    )


def _context():
    return InternalSessionContext(
        tenant_id="tenant-1",
        user_id="user-1",
        session_id="sess-1",
        trace_id="00000000000000000000000000000000",
        permissions=("bob_chat.use",),
        entitlements=("bob_chat.use",),
        roles=("support",),
        jti="ctx-test",
    )


def test_issue_and_validate_context_roundtrip():
    token = _signer().issue(_context(), now=1000)

    context = _signer().validate(token, now=1001)

    assert context.tenant_id == "tenant-1"
    assert context.user_id == "user-1"
    assert context.session_id == "sess-1"
    assert context.trace_id == "00000000000000000000000000000000"
    assert context.permissions == ("bob_chat.use",)
    assert context.entitlements == ("bob_chat.use",)
    assert context.roles == ("support",)


def test_rejects_replayed_jti():
    replay_store = InMemoryReplayStore()
    signer = _signer(replay_store=replay_store)
    token = signer.issue(_context(), now=1000)

    signer.validate(token, now=1001)

    with pytest.raises(InternalSessionContextError) as exc:
        signer.validate(token, now=1002)

    assert exc.value.reason_code == "internal_session_replayed"


def test_rejects_expired_context():
    token = _signer().issue(_context(), now=1000)

    with pytest.raises(InternalSessionContextError) as exc:
        _signer().validate(token, now=1301)

    assert exc.value.reason_code == "internal_session_expired"


def test_rejects_wrong_audience():
    token = _signer().issue(_context(), now=1000)
    signer = InternalSessionContextSigner(
        SECRET,
        kid="internal-session-test",
        audience="other-backend",
    )

    with pytest.raises(InternalSessionContextError) as exc:
        signer.validate(token, now=1001)

    assert exc.value.reason_code == "internal_session_invalid"


def test_rejects_alg_none_before_decode():
    header = _b64({"alg": "none", "typ": "JWT", "kid": "internal-session-test"})
    payload = _b64({"iss": "cde-b4f", "aud": "cde-internal-backend"})
    token = f"{header}.{payload}."

    with pytest.raises(InternalSessionContextError) as exc:
        _signer().validate(token, now=1001)

    assert exc.value.reason_code == "internal_session_algorithm_invalid"


def test_context_requires_trace_id():
    with pytest.raises(InternalSessionContextError) as exc:
        InternalSessionContext(
            tenant_id="tenant-1",
            user_id="user-1",
            session_id="sess-1",
            trace_id="",
        )

    assert exc.value.reason_code == "internal_session_context_invalid"


def test_middleware_injects_validated_context():
    app = FastAPI()
    signer = _signer()
    app.middleware("http")(InternalSessionContextMiddleware(signer))

    @app.get("/internal/example")
    async def example(request: Request):
        return {
            "tenant_id": request.state.tenant_id,
            "user_id": request.state.user_id,
            "trace_id": request.state.trace_id,
        }

    token = signer.issue(_context(), now=int(time.time()))

    response = TestClient(app).get(
        "/internal/example",
        headers={"X-Session-Context": token},
    )

    assert response.status_code == 200
    assert response.json() == {
        "tenant_id": "tenant-1",
        "user_id": "user-1",
        "trace_id": "00000000000000000000000000000000",
    }


def test_middleware_refuses_missing_context():
    app = FastAPI()
    app.middleware("http")(InternalSessionContextMiddleware(_signer()))

    @app.get("/internal/example")
    async def example():
        return {"ok": True}

    response = TestClient(app).get("/internal/example")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing internal session context"


def test_middleware_skips_health_path():
    app = FastAPI()
    app.middleware("http")(InternalSessionContextMiddleware(_signer()))

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def _b64(payload):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
