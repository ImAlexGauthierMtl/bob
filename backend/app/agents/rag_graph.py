"""RAG LangGraph pipeline — classify, retrieve, synthesize with citations.

Flow:
  classify_intent → needs_retrieval?
    → yes: retrieve → filter_authorize → synthesize_with_citations → store_trace
    → no:  direct_answer → store_trace
"""

import json
import uuid
from typing import TypedDict, Optional, List, Any

import structlog
from langgraph.graph import StateGraph, END

from app.agents.llm_client import llm_client
from app.config import settings

logger = structlog.get_logger(__name__)


class RAGState(TypedDict):
    """State that flows through the RAG pipeline."""

    # Input
    query: str
    tenant_id: str
    user_id: str
    user_email: str
    user_roles: List[str]
    user_modules: List[str]
    conversation_history: List[dict]

    # Classification
    needs_retrieval: bool
    intent_category: str

    # Retrieval
    retrieved_chunks: List[dict]

    # Synthesis
    answer: str
    citations: List[dict]
    correlation_id: str

    # Output
    status: str
    error: Optional[str]


async def classify_intent_node(state: RAGState) -> dict:
    """Classify whether the query needs RAG retrieval or can be answered directly."""
    query = state["query"]

    classification_prompt = f"""Classify this user query into one of these categories:
- "knowledge": needs retrieval from knowledge base (how-to, documentation, procedures)
- "data": needs CRM data lookup (specific contacts, organizations, opportunities)
- "action": user wants to perform an action (create, navigate, update)
- "chat": general conversation, greeting, or opinion

Query: "{query}"

Return JSON: {{"category": "...", "needs_retrieval": true/false}}
"""

    try:
        response = llm_client.chat(
            prompt=classification_prompt,
            system_prompt="You are a query classifier. Return only valid JSON.",
            json_mode=True,
            temperature=0.0,
            max_tokens=100,
            tenant_id=state.get("tenant_id"),
            trigger_source="RAG",
            correlation_id=state.get("correlation_id", ""),
        )
        result = json.loads(response)
        category = result.get("category", "chat")
        needs_retrieval = result.get("needs_retrieval", False)
    except Exception as e:
        logger.warning("rag_classify_fallback", error=str(e))
        category = "knowledge"
        needs_retrieval = True

    logger.info("rag_classified", query=query[:80], category=category, needs_retrieval=needs_retrieval)
    return {"intent_category": category, "needs_retrieval": needs_retrieval}


def route_after_classify(state: RAGState) -> str:
    """Route to retrieval or direct answer based on classification."""
    if state.get("needs_retrieval"):
        return "retrieve"
    return "direct_answer"


async def retrieve_node(state: RAGState) -> dict:
    """Retrieve relevant document chunks from the vector store."""
    from app.infrastructure.database import SessionLocal
    from app.rag.retriever import retrieve

    db = SessionLocal()
    try:
        results = retrieve(
            db=db,
            query=state["query"],
            tenant_id=state["tenant_id"],
            top_k=10,
            max_context_tokens=2000,
            user_roles=state.get("user_roles"),
            user_modules=state.get("user_modules"),
        )
        chunks = [
            {
                "chunk_id": r.chunk_id,
                "text": r.text,
                "source_type": r.source_type,
                "source_id": r.source_id,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in results
        ]
    except Exception as e:
        logger.error("rag_retrieve_error", error=str(e))
        chunks = []
    finally:
        db.close()

    logger.info("rag_retrieved", count=len(chunks), query=state["query"][:80])
    return {"retrieved_chunks": chunks}


async def filter_authorize_node(state: RAGState) -> dict:
    """Secondary access control filter on retrieved chunks.

    Defense-in-depth: the retriever already applies filters, but this
    node re-validates in case of race conditions or cache issues.
    """
    chunks = state.get("retrieved_chunks", [])
    user_roles = set(state.get("user_roles", []))

    authorized = []
    for chunk in chunks:
        required_role = chunk.get("metadata", {}).get("required_role")
        if required_role and required_role not in user_roles:
            logger.warning("rag_chunk_filtered", chunk_id=chunk["chunk_id"], reason="role_mismatch")
            continue
        authorized.append(chunk)

    return {"retrieved_chunks": authorized}


async def synthesize_with_citations_node(state: RAGState) -> dict:
    """Generate an answer using retrieved context with inline citations."""
    chunks = state.get("retrieved_chunks", [])
    query = state["query"]

    if not chunks:
        return {
            "answer": "I don't have enough information in my knowledge base to answer that question.",
            "citations": [],
        }

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source_label = chunk.get("metadata", {}).get("title", chunk.get("source_id", "unknown"))
        context_parts.append(f"[Source {i}: {source_label}]\n{chunk['text']}")

    context = "\n\n".join(context_parts)

    synthesis_prompt = f"""Answer the user's question using ONLY the provided context.

Rules:
- Cite sources using [1], [2], etc. after statements that come from the context
- If the context doesn't contain the answer, say so honestly
- Keep the answer concise and relevant
- Match the user's language

Context:
{context}

Question: {query}"""

    try:
        answer = llm_client.chat(
            prompt=synthesis_prompt,
            system_prompt="You are a helpful assistant that answers questions using provided context. Always cite your sources.",
            temperature=0.1,
            max_tokens=1024,
            tenant_id=state.get("tenant_id"),
            user_id=state.get("user_id"),
            trigger_source="RAG",
            correlation_id=state.get("correlation_id", ""),
        )
    except Exception as e:
        logger.error("rag_synthesize_error", error=str(e))
        answer = "I encountered an error generating the answer. Please try again."

    citations = [
        {
            "index": i + 1,
            "source_type": c.get("source_type"),
            "source_id": c.get("source_id"),
            "title": c.get("metadata", {}).get("title", ""),
        }
        for i, c in enumerate(chunks)
    ]

    return {"answer": answer, "citations": citations}


async def direct_answer_node(state: RAGState) -> dict:
    """Generate a direct answer without retrieval (for non-knowledge queries)."""
    return {
        "answer": "",
        "citations": [],
        "retrieved_chunks": [],
    }


async def store_trace_node(state: RAGState) -> dict:
    """Log the RAG execution trace and record metrics for observability."""
    chunks_count = len(state.get("retrieved_chunks", []))

    logger.info(
        "rag_trace",
        correlation_id=state.get("correlation_id"),
        query=state["query"][:80],
        intent=state.get("intent_category"),
        needs_retrieval=state.get("needs_retrieval"),
        chunks_retrieved=chunks_count,
        citations=len(state.get("citations", [])),
        answer_length=len(state.get("answer", "")),
    )

    # Record metrics
    try:
        from app.middleware.metrics import record_rag_query
        record_rag_query(state.get("intent_category", "unknown"), chunks_count)
    except Exception:
        pass

    # Track retrieval in usage tracker
    if state.get("needs_retrieval"):
        try:
            from app.infrastructure.database import SessionLocal
            from app.middleware.usage_tracker import UsageTracker
            from app.domain.entities.usage_transaction import TriggerSource

            db = SessionLocal()
            try:
                tracker = UsageTracker(db)
                tracker.track_retrieval(
                    tenant_id=state.get("tenant_id", ""),
                    user_id=state.get("user_id", ""),
                    user_email=state.get("user_email", ""),
                    query=state["query"],
                    chunks_retrieved=chunks_count,
                    chunks_after_filter=chunks_count,
                    trigger_source=TriggerSource.BOB_CHAT,
                    correlation_id=state.get("correlation_id", ""),
                )
            finally:
                db.close()
        except Exception as e:
            logger.warning("rag_usage_tracking_failed", error=str(e))

    return {"status": "done"}


def build_rag_graph() -> StateGraph:
    """Build and compile the RAG pipeline graph."""
    graph = StateGraph(RAGState)

    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("filter_authorize", filter_authorize_node)
    graph.add_node("synthesize_with_citations", synthesize_with_citations_node)
    graph.add_node("direct_answer", direct_answer_node)
    graph.add_node("store_trace", store_trace_node)

    graph.set_entry_point("classify_intent")

    graph.add_conditional_edges(
        "classify_intent",
        route_after_classify,
        {
            "retrieve": "retrieve",
            "direct_answer": "direct_answer",
        },
    )

    graph.add_edge("retrieve", "filter_authorize")
    graph.add_edge("filter_authorize", "synthesize_with_citations")
    graph.add_edge("synthesize_with_citations", "store_trace")
    graph.add_edge("direct_answer", "store_trace")
    graph.add_edge("store_trace", END)

    return graph.compile()


rag_pipeline = build_rag_graph()


async def run_rag_query(
    query: str,
    tenant_id: str,
    user_id: str,
    user_email: str,
    user_roles: list[str] | None = None,
    user_modules: list[str] | None = None,
    conversation_history: list[dict] | None = None,
) -> dict:
    """Run a RAG query through the pipeline.

    Returns dict with answer, citations, and metadata.
    """
    correlation_id = str(uuid.uuid4())

    initial_state: RAGState = {
        "query": query,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "user_email": user_email,
        "user_roles": user_roles or [],
        "user_modules": user_modules or [],
        "conversation_history": conversation_history or [],
        "needs_retrieval": False,
        "intent_category": "",
        "retrieved_chunks": [],
        "answer": "",
        "citations": [],
        "correlation_id": correlation_id,
        "status": "running",
        "error": None,
    }

    result = await rag_pipeline.ainvoke(initial_state)

    return {
        "answer": result.get("answer", ""),
        "citations": result.get("citations", []),
        "intent_category": result.get("intent_category", ""),
        "needs_retrieval": result.get("needs_retrieval", False),
        "chunks_retrieved": len(result.get("retrieved_chunks", [])),
        "correlation_id": correlation_id,
    }
