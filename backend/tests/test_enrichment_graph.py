"""Tests for enrichment graph — extraction status, error handling, partial results."""

import pytest
from unittest.mock import patch, MagicMock
import json


class TestExtractionNode:
    """Test extraction_node returns correct status based on extraction results."""

    @pytest.fixture
    def base_state(self):
        return {
            "organization_name": "Test Corp",
            "scraped_data": [{"url": "https://test.com", "content": "Test Corp is a tech company."}],
            "search_results": [],
            "regex_data": {},
            "hunter_contacts": [],
            "hunter_company": {},
            "tenant_id": "t1",
            "user_email": "test@test.com",
            "organization_id": "org-1",
        }

    @pytest.mark.asyncio
    async def test_both_extractions_succeed_returns_done(self, base_state):
        from app.agents.nodes.extraction_node import extraction_node

        flat_response = json.dumps({"industry": "Technology", "email": "info@test.com"})
        deep_response = json.dumps({"company_info": {"name": "Test Corp"}})

        with patch("app.agents.nodes.extraction_node.llm_client") as mock_llm:
            mock_llm.chat.side_effect = [flat_response, deep_response]
            result = await extraction_node(base_state)

        assert result["status"] == "done"
        assert result["extracted"]["industry"] == "Technology"
        assert result["organization_profile"]["company_info"]["name"] == "Test Corp"

    @pytest.mark.asyncio
    async def test_flat_fails_deep_succeeds_returns_partial(self, base_state):
        from app.agents.nodes.extraction_node import extraction_node

        deep_response = json.dumps({"company_info": {"name": "Test Corp"}})

        with patch("app.agents.nodes.extraction_node.llm_client") as mock_llm:
            mock_llm.chat.side_effect = [Exception("Groq timeout"), deep_response]
            result = await extraction_node(base_state)

        assert result["status"] == "partial"
        assert result["extracted"] == {}
        assert result["organization_profile"]["company_info"]["name"] == "Test Corp"

    @pytest.mark.asyncio
    async def test_both_fail_returns_error(self, base_state):
        from app.agents.nodes.extraction_node import extraction_node

        with patch("app.agents.nodes.extraction_node.llm_client") as mock_llm:
            mock_llm.chat.side_effect = [Exception("Groq timeout"), Exception("Groq timeout")]
            result = await extraction_node(base_state)

        assert result["status"] == "error"
        assert result["extracted"] == {}
        assert result["organization_profile"] == {}

    @pytest.mark.asyncio
    async def test_flat_succeeds_deep_fails_returns_partial(self, base_state):
        from app.agents.nodes.extraction_node import extraction_node

        flat_response = json.dumps({"industry": "Technology"})

        with patch("app.agents.nodes.extraction_node.llm_client") as mock_llm:
            mock_llm.chat.side_effect = [flat_response, Exception("LLM error")]
            result = await extraction_node(base_state)

        assert result["status"] == "partial"
        assert result["extracted"]["industry"] == "Technology"
        assert result["organization_profile"] == {}


class TestEnrichOrganizationUseCase:
    """Test that use case respects pipeline status."""

    @pytest.mark.asyncio
    async def test_error_status_does_not_mark_enriched(self):
        from app.application.use_cases.enrich_organization import EnrichOrganizationUseCase

        mock_db = MagicMock()
        mock_org = MagicMock()
        mock_org.name = "Test Corp"
        mock_org.website = "https://test.com"

        use_case = EnrichOrganizationUseCase(mock_db)
        use_case.repo = MagicMock()
        use_case.repo.get_by_id.return_value = mock_org

        with patch("app.application.use_cases.enrich_organization.run_enrichment") as mock_run:
            mock_run.return_value = {"status": "error", "extracted": {}, "organization_profile": {}}
            result = await use_case.execute("org-1", "t1", "test@test.com")

        assert result["status"] == "error"
        assert mock_org.ai_enriched != "Y"

    @pytest.mark.asyncio
    async def test_partial_status_marks_partial(self):
        from app.application.use_cases.enrich_organization import EnrichOrganizationUseCase

        mock_db = MagicMock()
        mock_org = MagicMock()
        mock_org.name = "Test Corp"
        mock_org.website = "https://test.com"
        mock_org.industry = None

        use_case = EnrichOrganizationUseCase(mock_db)
        use_case.repo = MagicMock()
        use_case.repo.get_by_id.return_value = mock_org

        with patch("app.application.use_cases.enrich_organization.run_enrichment") as mock_run:
            mock_run.return_value = {
                "status": "partial",
                "extracted": {"industry": "Tech"},
                "organization_profile": {},
            }
            result = await use_case.execute("org-1", "t1", "test@test.com")

        assert result["status"] == "partial"
        assert mock_org.ai_enriched == "P"


class TestEnrichmentRunModel:
    """Test the EnrichmentRun entity."""

    def test_complete_sets_fields(self):
        from app.domain.entities.enrichment_run import EnrichmentRun

        run = EnrichmentRun(organization_id="org-1", tenant_id="t1")
        run.complete(status="done", fields_updated=5, summary={"fields": ["industry"]})

        assert run.status == "done"
        assert run.fields_updated == 5
        assert run.completed_at is not None
        assert run.result_summary == {"fields": ["industry"]}

    def test_complete_error(self):
        from app.domain.entities.enrichment_run import EnrichmentRun

        run = EnrichmentRun(organization_id="org-1", tenant_id="t1")
        run.complete(status="error", error="LLM timeout")

        assert run.status == "error"
        assert run.error == "LLM timeout"
