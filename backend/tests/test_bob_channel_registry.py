"""Tests for Bob Channel Registry — tool filtering and channel capabilities."""

import pytest

from app.agents.bob_channel_registry import (
    CHANNELS,
    TOOL_CHANNEL_MAP,
    get_channel,
    get_tools_for_channel,
)


# ── Fake tool definitions (matching OpenAI function-calling format) ──

def _make_tool(name: str) -> dict:
    """Create a minimal tool definition matching the OpenAI format."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"Test tool: {name}",
            "parameters": {"type": "object", "properties": {}},
        },
    }


# Build a full set of test tools matching real tool names
ALL_TEST_TOOLS = [
    # UI manipulation tools
    _make_tool("navigate_to"),
    _make_tool("open_create_dialog"),
    _make_tool("ui_update_input"),
    _make_tool("ui_select_result"),
    _make_tool("ui_switch_tab"),
    _make_tool("start_crm_training"),
    _make_tool("search_and_open_entity"),
    _make_tool("change_training_slide"),
    # Artifact tools
    _make_tool("show_artifact"),
    _make_tool("invoke_deep_agent"),
    # Shared tools (not in TOOL_CHANNEL_MAP)
    _make_tool("search_contacts"),
    _make_tool("search_organizations"),
    _make_tool("create_contact"),
    _make_tool("create_organization"),
    _make_tool("create_opportunity"),
    _make_tool("get_pipeline_stats"),
    _make_tool("enrich_account"),
    _make_tool("search_rolodex"),
    _make_tool("bcc_update_profile"),
    _make_tool("bcc_get_profile"),
]

UI_TOOL_NAMES = {
    "navigate_to",
    "open_create_dialog",
    "ui_update_input",
    "ui_select_result",
    "ui_switch_tab",
    "start_crm_training",
    "search_and_open_entity",
    "change_training_slide",
}

ARTIFACT_TOOL_NAMES = {
    "show_artifact",
    "invoke_deep_agent",
}

SHARED_TOOL_NAMES = {
    "search_contacts",
    "search_organizations",
    "create_contact",
    "create_organization",
    "create_opportunity",
    "get_pipeline_stats",
    "enrich_account",
    "search_rolodex",
    "bcc_update_profile",
    "bcc_get_profile",
}

def _tool_names(tools: list[dict]) -> set[str]:
    """Extract tool names from a list of tool definitions."""
    return {t["function"]["name"] for t in tools}


# ── Channel definition tests ────────────────────────────────

class TestChannelDefinitions:
    """Verify channel capabilities are correctly defined."""

    def test_compact_can_manipulate_ui(self):
        assert CHANNELS["compact"].can_manipulate_ui is True

    def test_compact_cannot_show_artifacts(self):
        assert CHANNELS["compact"].can_show_artifacts is False

    def test_workspace_can_show_artifacts(self):
        assert CHANNELS["workspace"].can_show_artifacts is True

    def test_workspace_cannot_manipulate_ui(self):
        assert CHANNELS["workspace"].can_manipulate_ui is False

    def test_voice_app_can_speak_and_manipulate_ui(self):
        caps = CHANNELS["voice_app"]
        assert caps.can_speak is True
        assert caps.can_manipulate_ui is True
        assert caps.can_show_screen is True

    def test_voice_phone_can_only_speak(self):
        caps = CHANNELS["voice_phone"]
        assert caps.can_speak is True
        assert caps.can_manipulate_ui is False
        assert caps.can_show_artifacts is False
        assert caps.can_show_screen is False

    def test_unknown_channel_falls_back_to_compact(self):
        caps = get_channel("unknown_channel_xyz")
        assert caps == CHANNELS["compact"]


# ── Tool filtering tests ────────────────────────────────────

class TestToolFiltering:
    """Verify tools are correctly filtered by channel."""

    def test_compact_has_ui_tools(self):
        tools = get_tools_for_channel("compact", ALL_TEST_TOOLS)
        names = _tool_names(tools)
        # All UI tools should be present
        assert UI_TOOL_NAMES.issubset(names)

    def test_compact_excludes_artifact_tools(self):
        tools = get_tools_for_channel("compact", ALL_TEST_TOOLS)
        names = _tool_names(tools)
        # Artifact tools should NOT be present
        assert names.isdisjoint(ARTIFACT_TOOL_NAMES)

    def test_workspace_has_artifact_tools(self):
        tools = get_tools_for_channel("workspace", ALL_TEST_TOOLS)
        names = _tool_names(tools)
        assert ARTIFACT_TOOL_NAMES.issubset(names)

    def test_workspace_excludes_ui_tools(self):
        tools = get_tools_for_channel("workspace", ALL_TEST_TOOLS)
        names = _tool_names(tools)
        assert names.isdisjoint(UI_TOOL_NAMES)

    def test_voice_phone_has_no_ui_or_artifact_tools(self):
        tools = get_tools_for_channel("voice_phone", ALL_TEST_TOOLS)
        names = _tool_names(tools)
        assert names.isdisjoint(UI_TOOL_NAMES)
        assert names.isdisjoint(ARTIFACT_TOOL_NAMES)

    def test_shared_tools_available_in_all_channels(self):
        for channel in ["compact", "workspace", "voice_app", "voice_phone"]:
            tools = get_tools_for_channel(channel, ALL_TEST_TOOLS)
            names = _tool_names(tools)
            assert SHARED_TOOL_NAMES.issubset(names), (
                f"Shared tools missing in {channel}: {SHARED_TOOL_NAMES - names}"
            )

    def test_unknown_channel_defaults_to_compact_tools(self):
        compact_tools = get_tools_for_channel("compact", ALL_TEST_TOOLS)
        unknown_tools = get_tools_for_channel("unknown_xyz", ALL_TEST_TOOLS)
        assert _tool_names(compact_tools) == _tool_names(unknown_tools)

    def test_voice_app_has_ui_tools(self):
        """voice_app can manipulate UI (user sees the screen)."""
        tools = get_tools_for_channel("voice_app", ALL_TEST_TOOLS)
        names = _tool_names(tools)
        assert UI_TOOL_NAMES.issubset(names)

    def test_voice_app_excludes_artifact_tools(self):
        tools = get_tools_for_channel("voice_app", ALL_TEST_TOOLS)
        names = _tool_names(tools)
        assert names.isdisjoint(ARTIFACT_TOOL_NAMES)

    def test_empty_tools_returns_empty(self):
        tools = get_tools_for_channel("compact", [])
        assert tools == []


# ── Prompt tests ─────────────────────────────────────────────

class TestPrompts:
    """Verify channel-specific prompts are correctly assembled."""

    def test_compact_prompt_mentions_navigation(self):
        from app.agents.bob_prompts import get_system_prompt_for_channel
        prompt = get_system_prompt_for_channel("compact")
        assert "navigate" in prompt.lower()
        assert "navigate_to" in prompt

    def test_workspace_prompt_mentions_artifacts(self):
        from app.agents.bob_prompts import get_system_prompt_for_channel
        prompt = get_system_prompt_for_channel("workspace")
        assert "artifact" in prompt.lower()
        assert "show_artifact" in prompt

    def test_workspace_prompt_does_not_mention_navigate_to(self):
        from app.agents.bob_prompts import get_system_prompt_for_channel
        prompt = get_system_prompt_for_channel("workspace")
        assert "navigate_to" not in prompt

    def test_voice_phone_prompt_warns_no_screen(self):
        from app.agents.bob_prompts import get_system_prompt_for_channel
        prompt = get_system_prompt_for_channel("voice_phone")
        assert "ONLY" in prompt  # "You can ONLY speak"
        assert "screen" in prompt.lower()

    def test_all_prompts_contain_base(self):
        from app.agents.bob_prompts import get_system_prompt_for_channel, BASE_PROMPT
        for channel in ["compact", "workspace", "voice_app", "voice_phone"]:
            prompt = get_system_prompt_for_channel(channel)
            assert "You are Bob" in prompt
            assert "Tone Detection" in prompt

    def test_unknown_channel_defaults_to_compact(self):
        from app.agents.bob_prompts import get_system_prompt_for_channel
        compact = get_system_prompt_for_channel("compact")
        unknown = get_system_prompt_for_channel("xyz_unknown")
        assert compact == unknown
