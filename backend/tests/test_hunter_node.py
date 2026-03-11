"""Tests for hunter_node — Domain Search + Company Enrichment from Hunter.io."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json


class TestHunterNode:
    """Test hunter_node behavior with various configurations."""

    @pytest.fixture
    def base_state(self):
        return {
            "organization_id": "org-1",
            "organization_name": "Stripe",
            "tenant_id": "t1",
            "user_email": "test@test.com",
            "urls_to_scrape": ["https://www.stripe.com"],
            "hunter_contacts": [],
            "hunter_company": {},
            "search_results": [],
            "scraped_data": [],
            "regex_data": {},
            "extracted": {},
            "organization_profile": {},
            "status": "hunter",
            "error": None,
        }

    @pytest.mark.asyncio
    async def test_hunter_skip_when_no_api_key(self, base_state):
        """Skip gracefully when no Hunter API key is configured."""
        from app.agents.nodes.hunter_node import hunter_node

        with patch("app.agents.nodes.hunter_node.settings") as mock_settings:
            mock_settings.hunter_api_key = ""
            result = await hunter_node(base_state)

        assert result["hunter_contacts"] == []
        assert result["hunter_company"] == {}
        assert result["status"] == "scraping"

    @pytest.mark.asyncio
    async def test_hunter_skip_when_no_website(self, base_state):
        """Skip gracefully when no website URL is available."""
        from app.agents.nodes.hunter_node import hunter_node

        base_state["urls_to_scrape"] = []

        with patch("app.agents.nodes.hunter_node.settings") as mock_settings:
            mock_settings.hunter_api_key = "test-key"
            result = await hunter_node(base_state)

        assert result["hunter_contacts"] == []
        assert result["hunter_company"] == {}
        assert result["status"] == "scraping"

    @pytest.mark.asyncio
    async def test_hunter_domain_search_returns_contacts(self, base_state):
        """Domain Search returns contacts with email, position, LinkedIn."""
        from app.agents.nodes.hunter_node import hunter_node

        domain_search_response = {
            "data": {
                "emails": [
                    {
                        "value": "john@stripe.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "position": "CTO",
                        "position_raw": "Chief Technology Officer",
                        "seniority": "executive",
                        "department": "engineering",
                        "linkedin": "https://linkedin.com/in/johndoe",
                        "phone_number": "+1234567890",
                        "confidence": 95,
                        "verification": {"status": "valid"},
                    }
                ]
            }
        }
        company_response = {"data": {}}

        mock_responses = [
            MagicMock(status_code=200, json=lambda: domain_search_response, raise_for_status=lambda: None),
            MagicMock(status_code=200, json=lambda: company_response, raise_for_status=lambda: None),
        ]

        with patch("app.agents.nodes.hunter_node.settings") as mock_settings, \
             patch("app.agents.nodes.hunter_node.httpx.AsyncClient") as mock_client_class, \
             patch("app.agents.nodes.hunter_node._track_usage"):
            mock_settings.hunter_api_key = "test-key"
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=mock_responses)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await hunter_node(base_state)

        assert len(result["hunter_contacts"]) == 1
        contact = result["hunter_contacts"][0]
        assert contact["email"] == "john@stripe.com"
        assert contact["first_name"] == "John"
        assert contact["position"] == "CTO"
        assert contact["seniority"] == "executive"
        assert contact["linkedin"] == "https://linkedin.com/in/johndoe"
        assert contact["confidence"] == 95

    @pytest.mark.asyncio
    async def test_hunter_company_enrichment_returns_data(self, base_state):
        """Company Enrichment returns structured company data."""
        from app.agents.nodes.hunter_node import hunter_node

        domain_search_response = {"data": {"emails": []}}
        company_response = {
            "data": {
                "name": "Stripe",
                "description": "Payment processing",
                "category": {
                    "sector": "Information Technology",
                    "industry": "Internet Software & Services",
                    "subIndustry": "Internet",
                },
                "tags": ["fintech", "payments"],
                "foundedYear": 2010,
                "companyType": "privately held",
                "location": "San Francisco, CA",
                "phone": "+1 888 926 2289",
                "metrics": {"employees": "10K-50K", "estimatedAnnualRevenue": None},
                "geo": {"city": "South San Francisco", "state": "California"},
                "linkedin": {"handle": "company/stripe"},
                "twitter": {"handle": "stripe"},
                "facebook": {"handle": None},
                "youtube": {"handle": "stripe"},
                "tech": ["python", "react-js", "node-js"],
            }
        }

        mock_responses = [
            MagicMock(status_code=200, json=lambda: domain_search_response, raise_for_status=lambda: None),
            MagicMock(status_code=200, json=lambda: company_response, raise_for_status=lambda: None),
        ]

        with patch("app.agents.nodes.hunter_node.settings") as mock_settings, \
             patch("app.agents.nodes.hunter_node.httpx.AsyncClient") as mock_client_class, \
             patch("app.agents.nodes.hunter_node._track_usage"):
            mock_settings.hunter_api_key = "test-key"
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=mock_responses)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await hunter_node(base_state)

        company = result["hunter_company"]
        assert company["name"] == "Stripe"
        assert company["industry"] == "Internet Software & Services"
        assert company["founded_year"] == 2010
        assert company["employees"] == "10K-50K"
        assert company["social"]["linkedin"] == "https://linkedin.com/company/stripe"
        assert company["social"]["twitter"] == "https://twitter.com/stripe"
        assert "python" in company["tech_stack"]

    @pytest.mark.asyncio
    async def test_hunter_api_error_handled_gracefully(self, base_state):
        """API errors don't crash the pipeline — returns empty data."""
        from app.agents.nodes.hunter_node import hunter_node

        with patch("app.agents.nodes.hunter_node.settings") as mock_settings, \
             patch("app.agents.nodes.hunter_node.httpx.AsyncClient") as mock_client_class:
            mock_settings.hunter_api_key = "test-key"
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Hunter API timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await hunter_node(base_state)

        assert result["hunter_contacts"] == []
        assert result["hunter_company"] == {}
        assert result["status"] == "scraping"


class TestExtractDomain:
    """Test the _extract_domain helper."""

    def test_extract_from_full_url(self):
        from app.agents.nodes.hunter_node import _extract_domain
        assert _extract_domain("https://www.stripe.com/about") == "stripe.com"

    def test_extract_from_www_url(self):
        from app.agents.nodes.hunter_node import _extract_domain
        assert _extract_domain("https://www.example.com") == "example.com"

    def test_extract_from_bare_domain(self):
        from app.agents.nodes.hunter_node import _extract_domain
        assert _extract_domain("example.com") == "example.com"

    def test_extract_from_none(self):
        from app.agents.nodes.hunter_node import _extract_domain
        assert _extract_domain(None) is None

    def test_extract_from_empty(self):
        from app.agents.nodes.hunter_node import _extract_domain
        assert _extract_domain("") is None
