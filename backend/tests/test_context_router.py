"""Tests for the Context Router (Layer 0) — intelligent model routing.

Tests routing decisions, sticky routing, fallback behavior, and
the model registry. All LLM calls are mocked.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.agents.model_registry import (
    RoutingCategory,
    ModelProfile,
    get_model_for_category,
    get_all_profiles,
    QWEN3_32B,
    KIMI_K25,
    CLAUDE_SONNET,
    CostTier,
)
from app.agents.context_router import (
    RoutingDecision,
    route_message,
    _check_sticky_routing,
    ROUTE_TOOL,
    ROUTER_SYSTEM_PROMPT,
)


# ── Model Registry ──────────────────────────────────────────

class TestModelRegistry:
    """Tests for model_registry.py."""

    def test_routing_category_values(self):
        """RoutingCategory enum should have the expected values."""
        assert RoutingCategory.LIGHTWEIGHT == "lightweight"
        assert RoutingCategory.STRATEGIC == "strategic"
        assert RoutingCategory.TECHNICAL == "technical"
        assert RoutingCategory.PROCEDURE == "procedure"

    def test_get_model_lightweight(self):
        """LIGHTWEIGHT should map to Qwen3 32B."""
        profile = get_model_for_category(RoutingCategory.LIGHTWEIGHT)
        assert profile.id == "qwen3-32b"
        assert profile.provider == "groq"

    def test_get_model_strategic(self):
        """STRATEGIC should map to Kimi K2.5."""
        profile = get_model_for_category(RoutingCategory.STRATEGIC)
        assert profile.id == "kimi-k2.5"
        assert profile.provider == "openrouter"

    def test_get_model_technical(self):
        """TECHNICAL should map to Claude Sonnet."""
        profile = get_model_for_category(RoutingCategory.TECHNICAL)
        assert profile.id == "claude-sonnet"
        assert profile.provider == "openrouter"

    def test_get_model_procedure(self):
        """PROCEDURE should map to Qwen3 32B (BCC uses workflow engine)."""
        profile = get_model_for_category(RoutingCategory.PROCEDURE)
        assert profile.id == "qwen3-32b"

    def test_model_profiles_frozen(self):
        """ModelProfile should be frozen (immutable)."""
        with pytest.raises(AttributeError):
            QWEN3_32B.id = "changed"

    def test_get_all_profiles(self):
        """get_all_profiles should return all 3 models."""
        profiles = get_all_profiles()
        assert len(profiles) == 3
        assert "qwen3-32b" in profiles
        assert "kimi-k2.5" in profiles
        assert "claude-sonnet" in profiles

    def test_model_cost_tiers(self):
        """Models should have correct cost tiers."""
        assert QWEN3_32B.cost_tier == CostTier.FREE
        assert KIMI_K25.cost_tier == CostTier.LOW
        assert CLAUDE_SONNET.cost_tier == CostTier.MEDIUM


# ── Sticky Routing ──────────────────────────────────────────

class TestStickyRouting:
    """Tests for sticky routing logic."""

    def test_no_history(self):
        """No history should return None (no sticky)."""
        assert _check_sticky_routing([]) is None

    def test_lightweight_not_sticky(self):
        """LIGHTWEIGHT should never be sticky."""
        history = ["lightweight", "lightweight", "lightweight"]
        assert _check_sticky_routing(history) is None

    def test_strategic_becomes_sticky(self):
        """2+ STRATEGIC in last 3 should trigger sticky."""
        history = ["lightweight", "strategic", "strategic"]
        result = _check_sticky_routing(history)
        assert result == RoutingCategory.STRATEGIC

    def test_technical_becomes_sticky(self):
        """2+ TECHNICAL in last 3 should trigger sticky."""
        history = ["technical", "lightweight", "technical"]
        result = _check_sticky_routing(history)
        assert result == RoutingCategory.TECHNICAL

    def test_mixed_no_sticky(self):
        """Mixed high-tier categories should not be sticky."""
        history = ["strategic", "technical", "strategic"]
        # Last is strategic, but only 2 strategic vs 1 technical
        result = _check_sticky_routing(history)
        assert result == RoutingCategory.STRATEGIC

    def test_single_strategic_sticky(self):
        """Single strategic in short history should still be sticky."""
        history = ["strategic"]
        result = _check_sticky_routing(history)
        # 1 out of 1 = 100%, and min(2, len(1)) = 1 → sticky
        assert result == RoutingCategory.STRATEGIC


# ── Context Router ──────────────────────────────────────────

class TestContextRouter:
    """Tests for context_router.route_message()."""

    def _mock_groq_response(self, category: str, reason: str = "test"):
        """Create a mock Groq response with a route tool call."""
        import json

        mock_tc = MagicMock()
        mock_tc.function.name = "route"
        mock_tc.function.arguments = json.dumps({
            "category": category,
            "reason": reason,
        })

        mock_choice = MagicMock()
        mock_choice.message.tool_calls = [mock_tc]

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 50
        mock_usage.completion_tokens = 10

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        return mock_response

    @patch("app.agents.context_router.settings")
    @patch("app.agents.context_router.Groq")
    def test_route_lightweight(self, MockGroq, mock_settings):
        """Simple greeting should route to LIGHTWEIGHT."""
        mock_settings.router_enabled = True
        mock_settings.groq_api_key = "test-key"
        mock_settings.router_model = "qwen/qwen3-32b"
        mock_settings.router_max_tokens = 64

        MockGroq.return_value.chat.completions.create.return_value = (
            self._mock_groq_response("lightweight", "simple greeting")
        )

        result = route_message("Salut Bob")

        assert result.category == RoutingCategory.LIGHTWEIGHT
        assert result.model.id == "qwen3-32b"

    @patch("app.agents.context_router.settings")
    @patch("app.agents.context_router.Groq")
    def test_route_strategic(self, MockGroq, mock_settings):
        """Business strategy question should route to STRATEGIC."""
        mock_settings.router_enabled = True
        mock_settings.groq_api_key = "test-key"
        mock_settings.router_model = "qwen/qwen3-32b"
        mock_settings.router_max_tokens = 64

        MockGroq.return_value.chat.completions.create.return_value = (
            self._mock_groq_response("strategic", "market analysis request")
        )

        result = route_message("Comment attaquer le marché de la construction?")

        assert result.category == RoutingCategory.STRATEGIC
        assert result.model.id == "kimi-k2.5"

    @patch("app.agents.context_router.settings")
    @patch("app.agents.context_router.Groq")
    def test_route_technical(self, MockGroq, mock_settings):
        """Code request should route to TECHNICAL."""
        mock_settings.router_enabled = True
        mock_settings.groq_api_key = "test-key"
        mock_settings.router_model = "qwen/qwen3-32b"
        mock_settings.router_max_tokens = 64

        MockGroq.return_value.chat.completions.create.return_value = (
            self._mock_groq_response("technical", "code generation request")
        )

        result = route_message("Écris-moi un script Python pour analyser mes données")

        assert result.category == RoutingCategory.TECHNICAL
        assert result.model.id == "claude-sonnet"

    @patch("app.agents.context_router.settings")
    def test_router_disabled(self, mock_settings):
        """When router_enabled=False, should always return LIGHTWEIGHT."""
        mock_settings.router_enabled = False

        result = route_message("Strategic business question")

        assert result.category == RoutingCategory.LIGHTWEIGHT
        assert result.reason == "router_disabled"

    @patch("app.agents.context_router.settings")
    @patch("app.agents.context_router.Groq")
    def test_fallback_on_error(self, MockGroq, mock_settings):
        """On LLM error, should fallback to LIGHTWEIGHT."""
        mock_settings.router_enabled = True
        mock_settings.groq_api_key = "test-key"
        mock_settings.router_model = "qwen/qwen3-32b"
        mock_settings.router_max_tokens = 64

        MockGroq.return_value.chat.completions.create.side_effect = Exception("API down")

        result = route_message("Any message")

        assert result.category == RoutingCategory.LIGHTWEIGHT
        assert result.reason == "fallback"
        assert result.confidence == 0.5

    @patch("app.agents.context_router.settings")
    @patch("app.agents.context_router.Groq")
    def test_sticky_routing_applied(self, MockGroq, mock_settings):
        """Sticky routing should override LIGHTWEIGHT when momentum exists."""
        mock_settings.router_enabled = True
        mock_settings.groq_api_key = "test-key"
        mock_settings.router_model = "qwen/qwen3-32b"
        mock_settings.router_max_tokens = 64

        # LLM says lightweight, but history says strategic
        MockGroq.return_value.chat.completions.create.return_value = (
            self._mock_groq_response("lightweight", "seems simple")
        )

        result = route_message(
            "OK et quoi d'autre?",
            session_routing_history=["strategic", "strategic", "strategic"],
        )

        # Should override to strategic due to sticky routing
        assert result.category == RoutingCategory.STRATEGIC
        assert "sticky_routing" in result.reason

    @patch("app.agents.context_router.settings")
    @patch("app.agents.context_router.Groq")
    def test_no_sticky_when_topic_changes(self, MockGroq, mock_settings):
        """When LLM routes to a different high-tier, sticky should not apply."""
        mock_settings.router_enabled = True
        mock_settings.groq_api_key = "test-key"
        mock_settings.router_model = "qwen/qwen3-32b"
        mock_settings.router_max_tokens = 64

        # LLM says technical, history is strategic — LLM wins
        MockGroq.return_value.chat.completions.create.return_value = (
            self._mock_groq_response("technical", "user wants code now")
        )

        result = route_message(
            "Écris-moi du SQL",
            session_routing_history=["strategic", "strategic"],
        )

        assert result.category == RoutingCategory.TECHNICAL

    @patch("app.agents.context_router.settings")
    @patch("app.agents.context_router.Groq")
    def test_route_tool_schema(self, MockGroq, mock_settings):
        """ROUTE_TOOL schema should have the expected structure."""
        assert ROUTE_TOOL["function"]["name"] == "route"
        params = ROUTE_TOOL["function"]["parameters"]
        assert "category" in params["properties"]
        enums = params["properties"]["category"]["enum"]
        assert "lightweight" in enums
        assert "strategic" in enums
        assert "technical" in enums

    @patch("app.agents.context_router.settings")
    @patch("app.agents.context_router.Groq")
    def test_conversation_context_passed(self, MockGroq, mock_settings):
        """Conversation history should be included in the LLM call."""
        mock_settings.router_enabled = True
        mock_settings.groq_api_key = "test-key"
        mock_settings.router_model = "qwen/qwen3-32b"
        mock_settings.router_max_tokens = 64

        MockGroq.return_value.chat.completions.create.return_value = (
            self._mock_groq_response("lightweight")
        )

        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
        ]

        route_message("New question", conversation_history=history)

        # Verify the LLM was called with messages including history
        call_args = MockGroq.return_value.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        # Should be: system + 2 history + 1 user = 4
        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[-1]["content"] == "New question"
