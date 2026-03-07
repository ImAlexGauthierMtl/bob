"""Tests for Bob chat agent and routes."""

import pytest
from unittest.mock import patch


# ── Agent unit tests ─────────────────────────────────────────

class TestBobChatAgent:
    """Tests for BobChatAgent session management."""

    def setup_method(self):
        """Create a fresh agent instance for each test."""
        from app.agents.bob_chat_agent import BobChatAgent
        self.agent = BobChatAgent()

    def test_session_create(self):
        """Creating a session should return a valid ChatSession."""
        session = self.agent.get_or_create_session(
            session_id="test-session-1",
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        assert session is not None
        assert session.user_id == "user-1"
        assert session.tenant_id == "tenant-1"
        assert session.user_email == "test@croo.digital"
        assert session.turn_count == 0

    def test_session_reuse(self):
        """Getting the same session_id should return the same session."""
        session1 = self.agent.get_or_create_session(
            session_id="test-session-1",
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        session2 = self.agent.get_or_create_session(
            session_id="test-session-1",
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        assert session1 is session2

    def test_session_info(self):
        """Session info should return correct metadata."""
        self.agent.get_or_create_session(
            session_id="test-session-1",
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        info = self.agent.get_session_info("test-session-1")
        assert info is not None
        assert info["session_id"] == "test-session-1"
        assert info["user_id"] == "user-1"
        assert info["turn_count"] == 0
        assert info["message_count"] == 0

    def test_session_delete(self):
        """Deleting a session should remove it."""
        self.agent.get_or_create_session(
            session_id="test-session-1",
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )
        assert self.agent.delete_session("test-session-1") is True
        assert self.agent.get_session_info("test-session-1") is None

    def test_session_delete_nonexistent(self):
        """Deleting a nonexistent session should return False."""
        assert self.agent.delete_session("nonexistent") is False

    def test_list_sessions(self):
        """List sessions should return only the user's sessions."""
        self.agent.get_or_create_session(
            session_id="session-user1",
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="user1@croo.digital",
        )
        self.agent.get_or_create_session(
            session_id="session-user2",
            user_id="user-2",
            tenant_id="tenant-1",
            user_email="user2@croo.digital",
        )
        sessions = self.agent.list_sessions("user-1")
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "session-user1"

    @patch("app.agents.bob_chat_agent.Groq")
    def test_chat_response(self, MockGroq):
        """Chat should call Groq API and return (text, actions)."""
        # Mock the Groq SDK response (no tool calls)
        mock_choice = type("Choice", (), {
            "message": type("Message", (), {
                "content": "Hello, I'm Bob!",
                "tool_calls": None,
            })(),
            "finish_reason": "stop",
        })()
        mock_response = type("Response", (), {
            "choices": [mock_choice],
            "usage": type("Usage", (), {"prompt_tokens": 10, "completion_tokens": 5})(),
        })()
        MockGroq.return_value.chat.completions.create.return_value = mock_response

        self.agent.get_or_create_session(
            session_id="test-session",
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )

        text, actions = self.agent.chat("test-session", "Hi Bob!")
        assert text == "Hello, I'm Bob!"
        assert actions == []

        # Check that messages were stored
        info = self.agent.get_session_info("test-session")
        assert info["message_count"] == 2  # user + assistant
        assert info["turn_count"] == 1

    @patch("app.agents.bob_chat_agent.Groq")
    def test_chat_conversation_history(self, MockGroq):
        """Multiple turns should build conversation history."""
        mock_choice = type("Choice", (), {
            "message": type("Message", (), {
                "content": "Got it!",
                "tool_calls": None,
            })(),
        })()
        mock_response = type("Response", (), {
            "choices": [mock_choice],
        })()
        MockGroq.return_value.chat.completions.create.return_value = mock_response

        self.agent.get_or_create_session(
            session_id="test-session",
            user_id="user-1",
            tenant_id="tenant-1",
            user_email="test@croo.digital",
        )

        self.agent.chat("test-session", "First message")
        self.agent.chat("test-session", "Second message")

        info = self.agent.get_session_info("test-session")
        assert info["message_count"] == 4  # 2 user + 2 assistant
        assert info["turn_count"] == 2

    def test_chat_invalid_session(self):
        """Chat with invalid session should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            self.agent.chat("nonexistent", "Hello")


# ── Route integration tests ─────────────────────────────────

class TestBobRoutes:
    """Integration tests for Bob chat routes."""

    @patch("app.agents.bob_chat_agent.Groq")
    def test_chat_endpoint(self, MockGroq, client, auth_headers):
        """POST /api/v1/bob/chat should return a response."""
        mock_choice = type("Choice", (), {
            "message": type("Message", (), {
                "content": "Hello from Bob!",
                "tool_calls": None,
            })(),
        })()
        mock_response = type("Response", (), {
            "choices": [mock_choice],
        })()
        MockGroq.return_value.chat.completions.create.return_value = mock_response

        response = client.post(
            "/api/v1/bob/chat",
            json={"message": "Hi Bob!"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Hello from Bob!"
        assert "session_id" in data
        assert data["turn_count"] == 1

    def test_chat_empty_message(self, client, auth_headers):
        """POST /api/v1/bob/chat with empty message should return 400."""
        response = client.post(
            "/api/v1/bob/chat",
            json={"message": "   "},
            headers=auth_headers,
        )

        assert response.status_code == 400

    def test_chat_no_auth(self, client):
        """POST /api/v1/bob/chat without auth should return 401/403."""
        response = client.post(
            "/api/v1/bob/chat",
            json={"message": "Hi"},
        )
        assert response.status_code in (401, 403)

    def test_list_sessions(self, client, auth_headers):
        """GET /api/v1/bob/sessions should return list."""
        response = client.get(
            "/api/v1/bob/sessions",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @patch("app.agents.bob_chat_agent.Groq")
    def test_chat_then_list_sessions(self, MockGroq, client, auth_headers):
        """After chatting, list sessions should show the session."""
        mock_choice = type("Choice", (), {
            "message": type("Message", (), {
                "content": "Got it!",
                "tool_calls": None,
            })(),
        })()
        mock_response = type("Response", (), {
            "choices": [mock_choice],
        })()
        MockGroq.return_value.chat.completions.create.return_value = mock_response

        # Chat first
        chat_response = client.post(
            "/api/v1/bob/chat",
            json={"message": "Hello"},
            headers=auth_headers,
        )
        session_id = chat_response.json()["session_id"]

        # List sessions
        list_response = client.get(
            "/api/v1/bob/sessions",
            headers=auth_headers,
        )

        assert list_response.status_code == 200
        sessions = list_response.json()
        assert any(s["session_id"] == session_id for s in sessions)

    @patch("app.agents.bob_chat_agent.Groq")
    def test_delete_session(self, MockGroq, client, auth_headers):
        """DELETE /api/v1/bob/sessions/{id} should return 204."""
        mock_choice = type("Choice", (), {
            "message": type("Message", (), {
                "content": "Hello!",
                "tool_calls": None,
            })(),
        })()
        mock_response = type("Response", (), {
            "choices": [mock_choice],
        })()
        MockGroq.return_value.chat.completions.create.return_value = mock_response

        # Create a session first
        chat_response = client.post(
            "/api/v1/bob/chat",
            json={"message": "Hi"},
            headers=auth_headers,
        )
        session_id = chat_response.json()["session_id"]

        # Delete it
        response = client.delete(
            f"/api/v1/bob/sessions/{session_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

    def test_delete_session_not_found(self, client, auth_headers):
        """Deleting a nonexistent session should return 404."""
        response = client.delete(
            "/api/v1/bob/sessions/nonexistent-session",
            headers=auth_headers,
        )

        assert response.status_code == 404
