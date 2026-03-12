"""Tests for MS365 Integration API.

All MS Graph API calls are mocked — no real Microsoft requests.
"""

from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta


class TestMS365OAuth:
    """Test OAuth2 flow endpoints."""

    def test_get_auth_url(self, client, auth_headers):
        """GET /api/v1/ms365/auth-url returns a valid MS login URL."""
        response = client.get("/api/v1/ms365/auth-url", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert "login.microsoftonline.com" in data["auth_url"]
        assert "client_id" in data["auth_url"]

    @patch("app.presentation.routes.ms365_routes.graph_service")
    def test_callback_exchanges_code(self, mock_graph, client, auth_headers, db):
        """GET /api/v1/ms365/callback exchanges code → creates connection."""
        # Get user_id from auth
        me_response = client.get("/api/v1/auth/me", headers=auth_headers)
        user_id = me_response.json().get("id", "test-user-id")

        mock_graph.exchange_code_for_tokens = AsyncMock(return_value={
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_in": 3600,
            "scope": "Mail.Read Calendars.Read User.Read",
        })
        mock_graph.get_user_profile = AsyncMock(return_value={
            "id": "ms-user-123",
            "mail": "test@outlook.com",
            "displayName": "Test User",
        })

        response = client.get(
            f"/api/v1/ms365/callback?code=test-auth-code&state={user_id}",
            follow_redirects=False,
        )
        # Should redirect to frontend
        assert response.status_code in (302, 307)

    def test_get_connection_no_auth(self, client):
        """GET /api/v1/ms365/connection without auth returns 401."""
        response = client.get("/api/v1/ms365/connection")
        assert response.status_code == 401

    def test_get_connection_none(self, client, auth_headers):
        """GET /api/v1/ms365/connection when not connected returns null."""
        response = client.get("/api/v1/ms365/connection", headers=auth_headers)
        assert response.status_code == 200
        # Should return null/None when no connection
        assert response.json() is None


class TestMS365Connection:
    """Test connection management."""

    def test_disconnect_no_connection(self, client, auth_headers):
        """DELETE /api/v1/ms365/connection when not connected returns 404."""
        response = client.delete("/api/v1/ms365/connection", headers=auth_headers)
        assert response.status_code == 404


class TestMS365Sync:
    """Test sync endpoints."""

    def test_force_sync_no_connection(self, client, auth_headers):
        """POST /api/v1/ms365/sync without connection returns 404."""
        response = client.post("/api/v1/ms365/sync", headers=auth_headers)
        assert response.status_code == 404


class TestMS365Emails:
    """Test email listing endpoints."""

    def test_list_emails_empty(self, client, auth_headers):
        """GET /api/v1/ms365/emails returns empty list when no emails."""
        response = client.get("/api/v1/ms365/emails", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_emails_with_filters(self, client, auth_headers):
        """GET /api/v1/ms365/emails supports folder and search filters."""
        response = client.get(
            "/api/v1/ms365/emails?folder=inbox&search=test",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_get_email_not_found(self, client, auth_headers):
        """GET /api/v1/ms365/emails/{id} returns 404 for nonexistent."""
        response = client.get("/api/v1/ms365/emails/nonexistent", headers=auth_headers)
        assert response.status_code == 404


class TestMS365Events:
    """Test calendar event endpoints."""

    def test_list_events_empty(self, client, auth_headers):
        """GET /api/v1/ms365/events returns empty list when no events."""
        response = client.get("/api/v1/ms365/events", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_event_not_found(self, client, auth_headers):
        """GET /api/v1/ms365/events/{id} returns 404 for nonexistent."""
        response = client.get("/api/v1/ms365/events/nonexistent", headers=auth_headers)
        assert response.status_code == 404


class TestMS365Webhook:
    """Test webhook endpoint."""

    def test_webhook_validation(self, client):
        """POST /api/v1/ms365/webhook with validationToken returns it."""
        response = client.post(
            "/api/v1/ms365/webhook?validationToken=test-validation-token",
        )
        assert response.status_code == 200
        assert response.text == "test-validation-token"
