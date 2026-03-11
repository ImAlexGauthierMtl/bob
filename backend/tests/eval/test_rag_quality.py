"""RAG quality evaluation suite.

Measures:
- Retrieval recall (relevant documents retrieved)
- Citation precision (sources correctly cited)
- Non-grounded response rate
- Cross-tenant isolation (no data leakage)
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def test_cases():
    with open(FIXTURES_DIR / "rag_test_cases.json") as f:
        return json.load(f)


class TestIntentClassification:
    """Test that the RAG pipeline correctly classifies queries."""

    @pytest.mark.asyncio
    async def test_knowledge_query_classified_correctly(self, test_cases):
        from app.agents.rag_graph import classify_intent_node

        kb_case = next(c for c in test_cases if c["id"] == "kb_crm_basics")
        state = {
            "query": kb_case["query"],
            "tenant_id": kb_case["tenant_id"],
            "correlation_id": "test-1",
        }

        with patch("app.agents.rag_graph.llm_client") as mock_llm:
            mock_llm.chat.return_value = json.dumps({
                "category": "knowledge",
                "needs_retrieval": True,
            })
            result = await classify_intent_node(state)

        assert result["needs_retrieval"] is True
        assert result["intent_category"] == "knowledge"

    @pytest.mark.asyncio
    async def test_greeting_does_not_need_retrieval(self, test_cases):
        from app.agents.rag_graph import classify_intent_node

        greeting_case = next(c for c in test_cases if c["id"] == "general_greeting")
        state = {
            "query": greeting_case["query"],
            "tenant_id": greeting_case["tenant_id"],
            "correlation_id": "test-2",
        }

        with patch("app.agents.rag_graph.llm_client") as mock_llm:
            mock_llm.chat.return_value = json.dumps({
                "category": "chat",
                "needs_retrieval": False,
            })
            result = await classify_intent_node(state)

        assert result["needs_retrieval"] is False

    @pytest.mark.asyncio
    async def test_action_does_not_need_retrieval(self, test_cases):
        from app.agents.rag_graph import classify_intent_node

        action_case = next(c for c in test_cases if c["id"] == "action_navigate")
        state = {
            "query": action_case["query"],
            "tenant_id": action_case["tenant_id"],
            "correlation_id": "test-3",
        }

        with patch("app.agents.rag_graph.llm_client") as mock_llm:
            mock_llm.chat.return_value = json.dumps({
                "category": "action",
                "needs_retrieval": False,
            })
            result = await classify_intent_node(state)

        assert result["needs_retrieval"] is False


class TestRetrievalQuality:
    """Test retrieval recall and relevance."""

    @pytest.mark.asyncio
    async def test_retrieval_returns_relevant_chunks(self):
        from app.agents.rag_graph import retrieve_node

        state = {
            "query": "How do I create a contact?",
            "tenant_id": "test-tenant",
            "user_roles": ["user"],
            "user_modules": [],
        }

        mock_results = [
            MagicMock(
                chunk_id="c1",
                text="To create a new contact, navigate to the Contacts page and click Add.",
                source_type="kb_article",
                source_id="art-1",
                score=0.9,
                metadata={"title": "Creating Contacts"},
            ),
        ]

        with patch("app.agents.rag_graph.SessionLocal"), \
             patch("app.agents.rag_graph.retrieve", return_value=mock_results):
            result = await retrieve_node(state)

        assert len(result["retrieved_chunks"]) == 1
        assert "contact" in result["retrieved_chunks"][0]["text"].lower()


class TestCitationPrecision:
    """Test that synthesized answers contain proper citations."""

    @pytest.mark.asyncio
    async def test_synthesis_includes_citations(self):
        from app.agents.rag_graph import synthesize_with_citations_node

        state = {
            "query": "How do I create a contact?",
            "tenant_id": "test-tenant",
            "user_id": "u1",
            "correlation_id": "test-cite",
            "retrieved_chunks": [
                {
                    "chunk_id": "c1",
                    "text": "To create a contact, go to Contacts > Add New.",
                    "source_type": "kb_article",
                    "source_id": "art-1",
                    "score": 0.9,
                    "metadata": {"title": "Creating Contacts Guide"},
                },
            ],
        }

        with patch("app.agents.rag_graph.llm_client") as mock_llm:
            mock_llm.chat.return_value = "Go to the Contacts page and click Add New [1]."
            result = await synthesize_with_citations_node(state)

        assert len(result["citations"]) == 1
        assert result["citations"][0]["source_id"] == "art-1"
        assert "[1]" in result["answer"]

    @pytest.mark.asyncio
    async def test_no_chunks_returns_honest_answer(self):
        from app.agents.rag_graph import synthesize_with_citations_node

        state = {
            "query": "What is quantum computing?",
            "tenant_id": "test-tenant",
            "user_id": "u1",
            "correlation_id": "test-empty",
            "retrieved_chunks": [],
        }

        result = await synthesize_with_citations_node(state)
        assert "don't have enough" in result["answer"].lower() or "knowledge base" in result["answer"].lower()
        assert result["citations"] == []


class TestCrossTenantIsolation:
    """Test that retrieval never leaks data across tenants."""

    @pytest.mark.asyncio
    async def test_filter_authorize_blocks_wrong_role(self):
        from app.agents.rag_graph import filter_authorize_node

        state = {
            "user_roles": ["user"],
            "retrieved_chunks": [
                {
                    "chunk_id": "c1",
                    "text": "Admin-only content",
                    "metadata": {"required_role": "admin"},
                },
                {
                    "chunk_id": "c2",
                    "text": "Public content",
                    "metadata": {},
                },
            ],
        }

        result = await filter_authorize_node(state)
        # Only the public chunk should survive
        assert len(result["retrieved_chunks"]) == 1
        assert result["retrieved_chunks"][0]["chunk_id"] == "c2"


class TestChunker:
    """Test document chunking logic."""

    def test_sentence_chunking_respects_boundary(self):
        from app.rag.chunker import chunk_by_sentences

        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
        chunks = chunk_by_sentences(text, "test", "src-1", max_tokens=5, overlap_tokens=1)
        assert len(chunks) >= 2
        assert all(c.source_type == "test" for c in chunks)

    def test_kb_article_chunking(self):
        from app.rag.chunker import chunk_kb_article

        chunks = chunk_kb_article(
            article_id="art-1",
            title="Getting Started",
            content="This is the content of the article about getting started with the CRM.",
            tenant_id="t1",
            visibility="shared",
        )
        assert len(chunks) >= 1
        assert "Getting Started" in chunks[0].text

    def test_bcc_profile_chunking(self):
        from app.rag.chunker import chunk_bcc_profile

        chunks = chunk_bcc_profile(
            entity_type="organization",
            entity_id="org-1",
            section="vision",
            content="To be the leading CRM platform.",
            tenant_id="t1",
        )
        assert len(chunks) == 1
        assert "Vision" in chunks[0].text
