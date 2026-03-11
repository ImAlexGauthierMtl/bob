"""Tests for compound_node — Groq Compound deep intelligence."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.nodes.compound_node import (
    compound_node,
    _build_context,
    _parse_sections,
    _validate_section,
)


@pytest.fixture
def base_state():
    return {
        "organization_id": "org-123",
        "organization_name": "ASQ Consultants",
        "tenant_id": "tenant-1",
        "user_email": "test@example.com",
        "hunter_contacts": [
            {
                "first_name": "Jean-Philippe",
                "last_name": "Ranger",
                "email": "jp@asq.com",
                "position": "Associé",
                "department": "Executive",
            }
        ],
        "hunter_company": {
            "industry": "Insurance",
            "description": "Consulting firm",
            "phone": "+1 819 376 7319",
            "social": {"linkedin": "https://linkedin.com/company/asq"},
        },
        "search_results": [],
        "urls_to_scrape": [],
        "scraped_data": [{"url": "https://asq.com", "content": "About us page content"}],
        "regex_data": {},
        "extracted": {"industry": "Insurance"},
        "organization_profile": {
            "company_info": {"name": "ASQ Consultants"},
        },
        "intelligence_sections": [],
        "status": "done",
        "error": None,
    }


class TestParsesSections:
    """Test JSON parsing of Compound responses."""

    def test_parse_direct_json(self):
        content = json.dumps({
            "sections": [
                {"id": "competitors", "title": "Concurrents", "type": "tags", "items": ["NFP", "SFL"]}
            ]
        })
        sections = _parse_sections(content)
        assert len(sections) == 1
        assert sections[0]["id"] == "competitors"

    def test_parse_json_in_markdown_block(self):
        content = '```json\n{"sections": [{"id": "news", "title": "News", "type": "list", "items": ["Item 1"]}]}\n```'
        sections = _parse_sections(content)
        assert len(sections) == 1
        assert sections[0]["id"] == "news"

    def test_parse_returns_empty_on_invalid(self):
        sections = _parse_sections("This is not JSON at all")
        assert sections == []


class TestValidateSection:
    """Test section validation logic."""

    def test_valid_tags_section(self):
        assert _validate_section({"id": "test", "title": "Test", "type": "tags", "items": ["a"]})

    def test_valid_key_value_section(self):
        assert _validate_section({
            "id": "test", "title": "Test", "type": "key_value",
            "entries": [{"label": "L", "value": "V"}]
        })

    def test_valid_table_section(self):
        assert _validate_section({
            "id": "test", "title": "Test", "type": "table",
            "columns": ["A"], "rows": [["1"]]
        })

    def test_valid_list_section(self):
        assert _validate_section({"id": "test", "title": "Test", "type": "list", "items": ["x"]})

    def test_invalid_missing_id(self):
        assert not _validate_section({"title": "Test", "type": "tags", "items": ["a"]})

    def test_invalid_empty_items(self):
        assert not _validate_section({"id": "test", "title": "Test", "type": "tags", "items": []})

    def test_invalid_type(self):
        assert not _validate_section({"id": "test", "title": "Test", "type": "unknown"})


class TestBuildContext:
    """Test context building from state."""

    def test_includes_organization_name(self, base_state):
        context = _build_context(base_state)
        assert "ASQ Consultants" in context

    def test_includes_hunter_contacts(self, base_state):
        context = _build_context(base_state)
        assert "Jean-Philippe" in context
        assert "Ranger" in context

    def test_includes_hunter_company(self, base_state):
        context = _build_context(base_state)
        assert "Insurance" in context

    def test_includes_scraped_data(self, base_state):
        context = _build_context(base_state)
        assert "About us page content" in context


class TestCompoundNode:
    """Test the compound_node function."""

    @pytest.mark.asyncio
    @patch("app.agents.nodes.compound_node.settings")
    async def test_skip_when_no_api_key(self, mock_settings, base_state):
        mock_settings.groq_api_key = None
        result = await compound_node(base_state)
        assert result["intelligence_sections"] == []
        assert result["status"] == "done"

    @pytest.mark.asyncio
    @patch("app.agents.nodes.compound_node.settings")
    async def test_skip_when_no_data(self, mock_settings):
        mock_settings.groq_api_key = "test-key"
        empty_state = {
            "organization_id": "org-1",
            "organization_name": "Empty Org",
            "tenant_id": "t-1",
            "user_email": "test@test.com",
            "hunter_contacts": [],
            "hunter_company": {},
            "search_results": [],
            "urls_to_scrape": [],
            "scraped_data": [],
            "regex_data": {},
            "extracted": {},
            "organization_profile": {},
            "intelligence_sections": [],
            "status": "done",
            "error": None,
        }
        result = await compound_node(empty_state)
        assert result["intelligence_sections"] == []

    @pytest.mark.asyncio
    @patch("app.agents.nodes.compound_node._track_usage")
    @patch("app.agents.nodes.compound_node.settings")
    async def test_successful_compound_call(self, mock_settings, mock_track, base_state):
        mock_settings.groq_api_key = "test-key"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "sections": [
                {"id": "competitors", "title": "Concurrents", "icon": "fa-solid fa-chess",
                 "type": "tags", "items": ["NFP", "SFL"]},
                {"id": "online_presence", "title": "Présence en ligne", "icon": "fa-solid fa-globe",
                 "type": "key_value", "entries": [
                     {"label": "Google Maps", "value": "4.2/5"},
                 ]},
            ]
        })

        import sys
        mock_groq_module = MagicMock()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_module.Groq.return_value = mock_client
        sys.modules["groq"] = mock_groq_module

        try:
            result = await compound_node(base_state)
        finally:
            del sys.modules["groq"]

        assert len(result["intelligence_sections"]) == 2
        assert result["intelligence_sections"][0]["id"] == "competitors"
        assert result["intelligence_sections"][1]["type"] == "key_value"
        assert result["status"] == "done"

    @pytest.mark.asyncio
    @patch("app.agents.nodes.compound_node.settings")
    async def test_handles_api_error_gracefully(self, mock_settings, base_state):
        mock_settings.groq_api_key = "test-key"

        import sys
        mock_groq_module = MagicMock()
        mock_groq_module.Groq.side_effect = Exception("API error")
        sys.modules["groq"] = mock_groq_module

        try:
            result = await compound_node(base_state)
        finally:
            del sys.modules["groq"]

        assert result["intelligence_sections"] == []
        assert result["status"] == "done"

    @pytest.mark.asyncio
    @patch("app.agents.nodes.compound_node._track_usage")
    @patch("app.agents.nodes.compound_node.settings")
    async def test_filters_invalid_sections(self, mock_settings, mock_track, base_state):
        mock_settings.groq_api_key = "test-key"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "sections": [
                {"id": "valid", "title": "Valid", "type": "tags", "items": ["a"]},
                {"title": "No ID", "type": "tags", "items": ["b"]},  # Missing id
                {"id": "empty", "title": "Empty", "type": "tags", "items": []},  # Empty items
            ]
        })

        import sys
        mock_groq_module = MagicMock()
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq_module.Groq.return_value = mock_client
        sys.modules["groq"] = mock_groq_module

        try:
            result = await compound_node(base_state)
        finally:
            del sys.modules["groq"]

        assert len(result["intelligence_sections"]) == 1
        assert result["intelligence_sections"][0]["id"] == "valid"
