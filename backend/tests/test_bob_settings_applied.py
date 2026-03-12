"""Tests for Bob settings application — verify settings are actually applied."""

import pytest
from unittest.mock import patch, MagicMock


class TestChatSessionSerialization:
    """Test ChatSession serialization for session store."""

    def test_to_dict_and_from_dict_roundtrip(self):
        from app.agents.bob_chat_agent import ChatSession

        session = ChatSession(
            user_id="u1",
            tenant_id="t1",
            user_email="test@test.com",
            mission_prompt="Interview the CEO",
            mission_context={"org_id": "org-1"},
        )
        session.add_user_message("Hello")
        session.add_assistant_message("Hi there!")
        session.total_tokens_in = 100
        session.total_tokens_out = 50
        session.workflow_state = {"step": 2}
        session.workflow_resume_key = "step_2"

        data = session.to_dict()
        restored = ChatSession.from_dict(data)

        assert restored.user_id == "u1"
        assert restored.tenant_id == "t1"
        assert restored.user_email == "test@test.com"
        assert restored.mission_prompt == "Interview the CEO"
        assert restored.mission_context == {"org_id": "org-1"}
        assert len(restored.messages) == 2
        assert restored.messages[0]["role"] == "user"
        assert restored.total_tokens_in == 100
        assert restored.total_tokens_out == 50
        assert restored.turn_count == 1
        assert restored.workflow_state == {"step": 2}
        assert restored.workflow_resume_key == "step_2"

    def test_from_dict_with_missing_fields(self):
        from app.agents.bob_chat_agent import ChatSession

        minimal_data = {
            "user_id": "u1",
            "tenant_id": "t1",
            "user_email": "test@test.com",
        }
        restored = ChatSession.from_dict(minimal_data)
        assert restored.user_id == "u1"
        assert restored.messages == []
        assert restored.turn_count == 0
        assert restored.workflow_state is None


class TestKBAccessControl:
    """Test KB required_module and required_role enforcement."""

    def test_access_filter_excludes_restricted_articles(self):
        from unittest.mock import MagicMock
        from app.infrastructure.persistence.kb_repository import KBRepository

        mock_db = MagicMock()
        repo = KBRepository(mock_db)

        mock_query = MagicMock()
        filtered = repo._apply_access_filters(mock_query, user_roles=["user"], user_modules=["contacts"])
        # Should have been called with filter twice (role + module)
        assert filtered.filter.call_count == 2

    def test_access_filter_no_restrictions_passes_all(self):
        from unittest.mock import MagicMock
        from app.infrastructure.persistence.kb_repository import KBRepository

        mock_db = MagicMock()
        repo = KBRepository(mock_db)

        mock_query = MagicMock()
        # No roles/modules passed = no additional filters
        filtered = repo._apply_access_filters(mock_query, user_roles=None, user_modules=None)
        assert filtered.filter.call_count == 0


class TestProviderResilience:
    """Test retry decorator."""

    def test_retry_succeeds_after_failure(self):
        from app.infrastructure.provider_resilience import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Groq timeout")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted_raises(self):
        from app.infrastructure.provider_resilience import retry_with_backoff

        @retry_with_backoff(max_retries=1, base_delay=0.01)
        def always_fails():
            raise ConnectionError("permanent failure")

        with pytest.raises(ConnectionError, match="permanent failure"):
            always_fails()

    @pytest.mark.asyncio
    async def test_async_retry_succeeds(self):
        from app.infrastructure.provider_resilience import async_retry_with_backoff

        call_count = 0

        @async_retry_with_backoff(max_retries=1, base_delay=0.01)
        async def flaky_async():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("timeout")
            return "ok"

        result = await flaky_async()
        assert result == "ok"
        assert call_count == 2
