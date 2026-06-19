import asyncio

import httpx
import pytest

from shared.services import (
    BobCloudClient,
    BobCloudClientConfig,
    BobCloudModeError,
    BobCloudResponseError,
    create_bob_cloud_client_from_env,
    get_service_url,
)


def run(coro):
    return asyncio.run(coro)


def make_client(handler):
    transport = httpx.MockTransport(handler)
    return BobCloudClient(
        config=BobCloudClientConfig(
            base_url="http://bob-cloud-stub-api:8010",
            mode="stub",
            environment="test",
        ),
        transport=transport,
    )


def test_stub_mode_is_refused_in_production():
    with pytest.raises(BobCloudModeError, match="forbidden in production"):
        BobCloudClientConfig(
            base_url="http://bob-cloud-stub-api:8010",
            mode="stub",
            environment="production",
        )


def test_real_mode_requires_explicit_url(monkeypatch):
    monkeypatch.delenv("BOB_CLOUD_API_URL", raising=False)
    monkeypatch.setenv("BOB_CLOUD_MODE", "real")
    monkeypatch.setenv("ENV", "test")

    with pytest.raises(BobCloudModeError, match="BOB_CLOUD_API_URL is required"):
        create_bob_cloud_client_from_env()


def test_stub_mode_uses_docker_default(monkeypatch):
    monkeypatch.delenv("BOB_CLOUD_API_URL", raising=False)
    monkeypatch.delenv("BOB_CLOUD_STUB_API_URL", raising=False)
    monkeypatch.setenv("BOB_CLOUD_MODE", "stub")
    monkeypatch.setenv("ENV", "test")

    client = create_bob_cloud_client_from_env()

    assert client.config.base_url == "http://bob-cloud-stub-api:8010"


def test_service_registry_resolves_agent_control(monkeypatch):
    monkeypatch.delenv("AGENT_CONTROL_B4F_API_URL", raising=False)

    assert get_service_url("agent-control~b4f-api") == "http://agent-control-b4f-api:8008"


def test_get_session_forwards_safe_headers_only():
    captured = []

    def handler(request):
        captured.append(request)
        return httpx.Response(200, json={"authenticated": True, "source": "bob-cloud-stub"})

    client = make_client(handler)

    payload = run(
        client.get_session(
            forward_headers={
                "Cookie": "bob_cloud_session=abc",
                "X-Session-Context": "ctx",
                "X-Request-Id": "req-1",
                "X-Ignore-Me": "nope",
            }
        )
    )

    assert payload["authenticated"] is True
    request = captured[0]
    assert request.method == "GET"
    assert request.url.path == "/api/auth/v1/session"
    assert request.headers["cookie"] == "bob_cloud_session=abc"
    assert request.headers["x-session-context"] == "ctx"
    assert request.headers["x-request-id"] == "req-1"
    assert "x-ignore-me" not in request.headers


def test_get_session_response_preserves_cookie_headers():
    def handler(request):
        return httpx.Response(
            200,
            headers={"Set-Cookie": "bob_cloud_session=abc; HttpOnly; Path=/"},
            json={"authenticated": True},
        )

    client = make_client(handler)

    response = run(client.get_session_response())

    assert response.json()["authenticated"] is True
    assert response.headers["set-cookie"] == "bob_cloud_session=abc; HttpOnly; Path=/"


def test_check_capability_posts_expected_payload():
    captured = []

    def handler(request):
        captured.append(request)
        return httpx.Response(
            200,
            json={"capability": "bob_chat.use", "status": "enabled", "remaining": 10},
        )

    client = make_client(handler)

    payload = run(client.check_capability("bob_chat.use"))

    assert payload["status"] == "enabled"
    request = captured[0]
    assert request.method == "POST"
    assert request.url.path == "/api/platform/v1/entitlements/check"
    assert request.read() == b'{"capability":"bob_chat.use"}'


def test_bob_cloud_error_preserves_status_and_detail():
    def handler(request):
        return httpx.Response(403, json={"code": "license_missing"})

    client = make_client(handler)

    with pytest.raises(BobCloudResponseError) as exc:
        run(
            client.create_invitation(
                {"email": "test@example.com"},
                idempotency_key="invite-1",
            )
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == {"code": "license_missing"}
    assert exc.value.path == "/api/iam/v1/invitations"


def test_iam_mutation_sends_idempotency_key():
    captured = []

    def handler(request):
        captured.append(request)
        return httpx.Response(200, json={"id": "membership-local-admin"})

    client = make_client(handler)

    payload = run(
        client.update_membership(
            "membership-local-admin",
            {"role_codes": ["admin"]},
            idempotency_key="membership-update-1",
        )
    )

    assert payload["id"] == "membership-local-admin"
    request = captured[0]
    assert request.method == "PATCH"
    assert request.url.path == "/api/iam/v1/memberships/membership-local-admin"
    assert request.headers["idempotency-key"] == "membership-update-1"


def test_platform_management_lists_use_expected_paths():
    captured = []

    def handler(request):
        captured.append(request)
        return httpx.Response(200, json={"items": []})

    client = make_client(handler)

    assert run(client.list_tenants()) == {"items": []}
    assert run(client.list_licenses()) == {"items": []}

    assert captured[0].method == "GET"
    assert captured[0].url.path == "/api/platform/v1/tenants"
    assert captured[1].method == "GET"
    assert captured[1].url.path == "/api/platform/v1/licenses"


def test_platform_management_mutations_send_idempotency_key():
    captured = []

    def handler(request):
        captured.append(request)
        if request.url.path.endswith("/tenant-croo-local"):
            return httpx.Response(200, json={"id": "tenant-croo-local"})
        return httpx.Response(200, json={"code": "bob_chat.use"})

    client = make_client(handler)

    tenant = run(
        client.update_tenant(
            "tenant-croo-local",
            {"name": "Croo Local QA"},
            idempotency_key="tenant-update-1",
        )
    )
    license_payload = run(
        client.update_license(
            "bob_chat.use",
            {"status": "disabled"},
            idempotency_key="license-update-1",
        )
    )

    assert tenant["id"] == "tenant-croo-local"
    assert license_payload["code"] == "bob_chat.use"
    assert captured[0].method == "PATCH"
    assert captured[0].url.path == "/api/platform/v1/tenants/tenant-croo-local"
    assert captured[0].headers["idempotency-key"] == "tenant-update-1"
    assert captured[1].method == "PATCH"
    assert captured[1].url.path == "/api/platform/v1/licenses/bob_chat.use"
    assert captured[1].headers["idempotency-key"] == "license-update-1"
