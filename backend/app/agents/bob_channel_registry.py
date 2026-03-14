"""Bob Channel Registry — declares channel capabilities and tool filtering.

Each channel (compact, workspace, voice_app, voice_phone) has a set of
capabilities that determine which tools are available and how Bob delivers
information. The registry is the single source of truth for channel behavior.

Architecture reference: Couche 1 — La couche relationnelle.
"""

from dataclasses import dataclass
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ChannelCapabilities:
    """Declares what a channel can and cannot do.

    These flags drive tool filtering and prompt selection:
    - can_manipulate_ui:  Bob can open pages, fill forms, click buttons
    - can_show_artifacts: Bob can render rich inline cards in the feed
    - can_show_screen:    The user sees the app screen (visual feedback)
    - can_speak:          Bob can produce audio (TTS)
    - can_hear:           Bob can receive audio (STT)
    - can_show_quick_actions: Bob can display clickable action buttons
    """

    can_manipulate_ui: bool
    can_show_artifacts: bool
    can_show_screen: bool
    can_speak: bool
    can_hear: bool
    can_show_quick_actions: bool


# ── Channel definitions ──────────────────────────────────────

CHANNELS: dict[str, ChannelCapabilities] = {
    "compact": ChannelCapabilities(
        can_manipulate_ui=True,
        can_show_artifacts=False,
        can_show_screen=True,
        can_speak=False,
        can_hear=False,
        can_show_quick_actions=True,
    ),
    "workspace": ChannelCapabilities(
        can_manipulate_ui=False,
        can_show_artifacts=True,
        can_show_screen=True,
        can_speak=False,
        can_hear=False,
        can_show_quick_actions=True,
    ),
    "voice_app": ChannelCapabilities(
        can_manipulate_ui=True,
        can_show_artifacts=False,
        can_show_screen=True,
        can_speak=True,
        can_hear=True,
        can_show_quick_actions=False,
    ),
    "voice_phone": ChannelCapabilities(
        can_manipulate_ui=False,
        can_show_artifacts=False,
        can_show_screen=False,
        can_speak=True,
        can_hear=True,
        can_show_quick_actions=False,
    ),
}

DEFAULT_CHANNEL = "compact"


def get_channel(channel: str) -> ChannelCapabilities:
    """Get channel capabilities, falling back to compact if unknown."""
    caps = CHANNELS.get(channel)
    if caps is None:
        logger.warning("unknown_channel_fallback", channel=channel, fallback=DEFAULT_CHANNEL)
        caps = CHANNELS[DEFAULT_CHANNEL]
    return caps


# ── Tool-to-channel mapping ─────────────────────────────────
# Declares which channels each tool is allowed in.
# Tools NOT listed here are available in ALL channels (shared).

TOOL_CHANNEL_MAP: dict[str, list[str]] = {
    # UI manipulation tools — only where Bob can control the interface
    "navigate_to":            ["compact", "voice_app"],
    "open_create_dialog":     ["compact", "voice_app"],
    "ui_update_input":        ["compact", "voice_app"],
    "ui_select_result":       ["compact", "voice_app"],
    "ui_switch_tab":          ["compact", "voice_app"],
    "start_crm_training":     ["compact", "voice_app"],
    "search_and_open_entity": ["compact", "voice_app"],
    "change_training_slide":  ["compact", "voice_app"],
    # Artifact tools — only where Bob can render inline cards
    "show_artifact":          ["workspace"],
    "invoke_deep_agent":      ["workspace"],
}

# Tools NOT in TOOL_CHANNEL_MAP are considered shared (available everywhere):
# create_contact, create_organization, create_opportunity,
# search_contacts, search_organizations, search_rolodex,
# get_pipeline_stats, get_recent_activities, enrich_account,
# bcc_update_profile, bcc_get_profile, link_product_to_opportunity


def get_tools_for_channel(
    channel: str,
    all_tools: list[dict],
) -> list[dict]:
    """Filter a list of tool definitions to only those allowed for the channel.

    Args:
        channel: Channel identifier (compact, workspace, voice_app, voice_phone)
        all_tools: Full list of tool definitions (OpenAI function-calling format)

    Returns:
        Filtered list of tool definitions for the given channel.
    """
    # Normalize unknown channels to default
    if channel not in CHANNELS:
        logger.warning("unknown_channel_tool_fallback", channel=channel, fallback=DEFAULT_CHANNEL)
        channel = DEFAULT_CHANNEL

    filtered = []
    for tool in all_tools:
        tool_name = tool.get("function", {}).get("name", "")
        allowed_channels = TOOL_CHANNEL_MAP.get(tool_name)

        if allowed_channels is None:
            # Tool is not in the map → shared, available everywhere
            filtered.append(tool)
        elif channel in allowed_channels:
            # Tool is explicitly allowed for this channel
            filtered.append(tool)
        # else: tool is restricted and this channel is not in the list → skip

    logger.debug(
        "tools_filtered_for_channel",
        channel=channel,
        total=len(all_tools),
        filtered=len(filtered),
        excluded=[
            t.get("function", {}).get("name", "")
            for t in all_tools
            if t not in filtered
        ],
    )
    return filtered
