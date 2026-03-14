"""Workspace Agent — Agentic CRM Chat powered by Kimi K2 via Groq.

When channel == "workspace", Bob becomes an intelligent agent with tool-calling.
Kimi K2 decides when to query CRM data or search the web, then synthesizes
a contextual response grounded in real business data.

Tools:
  - query_crm: Search/filter CRM entities (accounts, contacts, opportunities)
  - get_pipeline_stats: Pipeline KPIs (by stage, value, win rate)
  - get_account_details: Full account profile + related records
  - search_web: Serper web search for market data / validation
  - get_recent_activities: Recent CRM activities (last N days)
"""

import json
import structlog
from typing import Optional

from groq import Groq
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.config import settings
from app.agents.advisor_context_loader import load_advisor_context
from app.agents.crm_context_loader import load_crm_context

logger = structlog.get_logger(__name__)

MAX_TOOL_ROUNDS = 5  # Max agentic loop iterations

# ── System Prompt ────────────────────────────────────────────

WORKSPACE_SYSTEM_PROMPT = """\
You are **Bob**, a CRM-native business intelligence assistant.

## Your Mode
You are in **Workspace Mode** — a full, rich conversational interface.
You have direct access to the company's CRM data via tools.

## How to Work
1. **Think first**: Analyze what the user needs.
2. **Use tools**: Call CRM tools to get real data. NEVER fabricate numbers.
3. **Search web**: When discussing market trends, competitors, or benchmarks, use search_web.
4. **Synthesize**: Combine CRM data + web data + organizational context into actionable insights.

## Communication Style
- Be direct, structured, and professional
- Use headers, bullet points, and bold for key insights
- Quantify everything — real numbers from CRM, not estimates
- Respond in the same language as the user (French or English)
- When presenting CRM data, format it clearly with tables or lists

## What You Know (Organizational Context)
{org_context}

## CRM Snapshot
{crm_context}

## Rules — CRITICAL
- ALWAYS use tools to get current data before answering CRM questions
- NEVER make up data — if you can't find it, say so
- For strategic advice, combine CRM data with web research
- If the user asks to create/modify records, explain what action would be needed
  (you observe data, you don't modify it in workspace mode)

## Anti-Hallucination Policy — STRICT
- **NEVER invent URLs, links, or references.** Every URL you cite MUST come from
  a search_web result. If you don't have a real URL, don't include one.
- **NEVER fabricate statistics, percentages, or market data.** If you need external
  numbers (market size, industry benchmarks, competitor data), you MUST call
  search_web first and only report what the search results actually say.
- **NEVER cite fake studies, reports, or organizations.** Only reference sources
  that appear in your search_web results.
- **Always attribute sources.** When citing external data, include the source title
  and real URL from the search results.
- **If search_web returns no relevant results, say so honestly.** Do not fill the
  gap with invented data. Say: "Je n'ai pas trouvé de source fiable pour cette
  information."
- **CRM data is factual** — numbers from query_crm and get_pipeline_stats are real.
  External claims are NOT factual unless verified via search_web.
"""

# ── Tool Definitions (Groq tool-calling schema) ──────────────

CRM_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_crm",
            "description": (
                "Search and filter CRM entities. Use this to find accounts, contacts, "
                "or opportunities matching specific criteria."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["organization", "contact", "opportunity"],
                        "description": "The CRM entity type to query",
                    },
                    "search_term": {
                        "type": "string",
                        "description": "Optional name or keyword to search for (case-insensitive)",
                    },
                    "filters": {
                        "type": "object",
                        "description": (
                            "Optional filters. For organization: {status, industry}. "
                            "For opportunity: {stage, min_amount, max_amount}. "
                            "For contact: {organization_name}."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default: 10)",
                    },
                },
                "required": ["entity_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pipeline_stats",
            "description": (
                "Get pipeline statistics: total deals, value by stage, "
                "average deal size, win rate. Use this for pipeline overviews."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_account_details",
            "description": (
                "Get full details for a specific account/organization, "
                "including contacts, opportunities, and recent activities."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "account_name": {
                        "type": "string",
                        "description": "Name of the account to look up",
                    },
                },
                "required": ["account_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Search the web for market data, competitor info, industry trends, "
                "or benchmarks. Use this to enrich responses with external data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_activities",
            "description": (
                "Get recent CRM activities (calls, emails, meetings, tasks) "
                "from the last N days."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 7)",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_contact_client_map",
            "description": (
                "Get the Client Map 360° for a contact. Returns MEDDPICC quadrant data "
                "(pain points, decision process, champion, competition), "
                "behavioral profile (DISC, decision speed, communication tips), "
                "and recent Golden Notes (verbatim quotes, emotional climate)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "UUID of the contact to retrieve Client Map for",
                    },
                },
                "required": ["contact_id"],
            },
        },
    },
]


# ── Tool Executors ───────────────────────────────────────────

def _exec_query_crm(
    db: Session,
    tenant_id: str,
    entity_type: str,
    search_term: str = "",
    filters: dict | None = None,
    limit: int = 10,
) -> str:
    """Execute a CRM query and return formatted results."""
    from app.domain.entities.organization import Organization
    from app.domain.entities.contact import Contact
    from app.domain.entities.opportunity import Opportunity

    filters = filters or {}
    results = []

    try:
        if entity_type == "organization":
            q = db.query(Organization).filter(Organization.tenant_id == tenant_id)
            if search_term:
                q = q.filter(Organization.name.ilike(f"%{search_term}%"))
            if filters.get("status"):
                q = q.filter(Organization.status == filters["status"])
            if filters.get("industry"):
                q = q.filter(Organization.industry.ilike(f"%{filters['industry']}%"))
            orgs = q.limit(limit).all()
            for o in orgs:
                results.append({
                    "name": o.name,
                    "status": o.status or "N/A",
                    "industry": o.industry or "N/A",
                    "phone": o.phone or "",
                    "website": o.website or "",
                })

        elif entity_type == "contact":
            q = db.query(Contact).filter(Contact.tenant_id == tenant_id)
            if search_term:
                q = q.filter(
                    (Contact.first_name.ilike(f"%{search_term}%"))
                    | (Contact.last_name.ilike(f"%{search_term}%"))
                    | (Contact.email.ilike(f"%{search_term}%"))
                )
            contacts = q.limit(limit).all()
            for c in contacts:
                results.append({
                    "name": f"{c.first_name or ''} {c.last_name or ''}".strip(),
                    "email": c.email or "",
                    "phone": c.phone or "",
                    "title": c.title or "",
                })

        elif entity_type == "opportunity":
            q = db.query(Opportunity).filter(Opportunity.tenant_id == tenant_id)
            if search_term:
                q = q.filter(Opportunity.name.ilike(f"%{search_term}%"))
            if filters.get("stage"):
                q = q.filter(Opportunity.stage == filters["stage"])
            if filters.get("min_amount"):
                q = q.filter(Opportunity.amount >= float(filters["min_amount"]))
            if filters.get("max_amount"):
                q = q.filter(Opportunity.amount <= float(filters["max_amount"]))
            opps = q.order_by(desc(Opportunity.amount)).limit(limit).all()
            for o in opps:
                results.append({
                    "name": o.name,
                    "stage": o.stage or "N/A",
                    "amount": f"{o.amount or 0:,.0f}$",
                    "close_date": str(o.close_date) if o.close_date else "N/A",
                })

    except Exception as e:
        return json.dumps({"error": str(e)})

    return json.dumps({
        "entity_type": entity_type,
        "count": len(results),
        "results": results,
    }, ensure_ascii=False)


def _exec_get_pipeline_stats(db: Session, tenant_id: str) -> str:
    """Get pipeline statistics."""
    from app.domain.entities.opportunity import Opportunity

    try:
        total = db.query(func.count(Opportunity.id)).filter(
            Opportunity.tenant_id == tenant_id
        ).scalar() or 0

        total_value = db.query(func.sum(Opportunity.amount)).filter(
            Opportunity.tenant_id == tenant_id
        ).scalar() or 0

        avg_deal = total_value / total if total > 0 else 0

        # By stage
        stages = db.query(
            Opportunity.stage,
            func.count(Opportunity.id),
            func.sum(Opportunity.amount),
        ).filter(
            Opportunity.tenant_id == tenant_id,
        ).group_by(Opportunity.stage).all()

        stage_data = []
        for stage, count, value in stages:
            stage_data.append({
                "stage": stage or "Unset",
                "count": count,
                "value": f"{value or 0:,.0f}$",
            })

        # Won deals
        won = db.query(func.count(Opportunity.id)).filter(
            Opportunity.tenant_id == tenant_id,
            Opportunity.stage == "Closed Won",
        ).scalar() or 0

        lost = db.query(func.count(Opportunity.id)).filter(
            Opportunity.tenant_id == tenant_id,
            Opportunity.stage == "Closed Lost",
        ).scalar() or 0

        closed = won + lost
        win_rate = (won / closed * 100) if closed > 0 else 0

        return json.dumps({
            "total_deals": total,
            "total_value": f"{total_value:,.0f}$",
            "average_deal_size": f"{avg_deal:,.0f}$",
            "win_rate": f"{win_rate:.1f}%",
            "by_stage": stage_data,
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)})


def _exec_get_account_details(db: Session, tenant_id: str, account_name: str) -> str:
    """Get full details for a specific account."""
    from app.domain.entities.organization import Organization
    from app.domain.entities.contact import Contact
    from app.domain.entities.opportunity import Opportunity

    try:
        org = db.query(Organization).filter(
            Organization.tenant_id == tenant_id,
            Organization.name.ilike(f"%{account_name}%"),
        ).first()

        if not org:
            return json.dumps({"error": f"Account '{account_name}' not found"})

        # Contacts
        contacts = db.query(Contact).filter(
            Contact.tenant_id == tenant_id,
            Contact.organization_id == org.id,
        ).all()

        contact_list = [
            {
                "name": f"{c.first_name or ''} {c.last_name or ''}".strip(),
                "email": c.email or "",
                "title": c.title or "",
            }
            for c in contacts
        ]

        # Opportunities
        opps = db.query(Opportunity).filter(
            Opportunity.tenant_id == tenant_id,
            Opportunity.organization_id == org.id,
        ).all()

        opp_list = [
            {
                "name": o.name,
                "stage": o.stage or "N/A",
                "amount": f"{o.amount or 0:,.0f}$",
            }
            for o in opps
        ]

        total_pipeline = sum(o.amount or 0 for o in opps)

        return json.dumps({
            "name": org.name,
            "status": org.status or "N/A",
            "industry": org.industry or "N/A",
            "phone": org.phone or "",
            "website": org.website or "",
            "contacts": contact_list,
            "contacts_count": len(contact_list),
            "opportunities": opp_list,
            "opportunities_count": len(opp_list),
            "total_pipeline_value": f"{total_pipeline:,.0f}$",
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)})


def _exec_search_web(query: str, num_results: int = 5) -> str:
    """Search the web via Serper."""
    import httpx

    if not settings.serper_api_key:
        return json.dumps({"error": "Web search not configured"})

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": num_results},
                headers={
                    "X-API-KEY": settings.serper_api_key,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("organic", [])[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("link", ""),
            })

        return json.dumps({"query": query, "results": results}, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)})


def _exec_get_recent_activities(db: Session, tenant_id: str, days: int = 7) -> str:
    """Get recent CRM activities."""
    from app.domain.entities.activity import Activity
    from datetime import datetime, timedelta

    try:
        since = datetime.utcnow() - timedelta(days=days)
        activities = db.query(Activity).filter(
            Activity.tenant_id == tenant_id,
            Activity.created_at >= since,
        ).order_by(desc(Activity.created_at)).limit(20).all()

        results = []
        for a in activities:
            results.append({
                "type": a.type or "N/A",
                "subject": a.subject or "N/A",
                "date": str(a.created_at.date()) if a.created_at else "N/A",
                "notes": (a.notes or "")[:100],
            })

        return json.dumps({
            "period": f"Last {days} days",
            "count": len(results),
            "activities": results,
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e), "note": "Activity module may not be configured"})


# ── Tool Router ──────────────────────────────────────────────

def _execute_tool(
    tool_name: str,
    tool_args: dict,
    db: Session,
    tenant_id: str,
) -> str:
    """Route a tool call to the appropriate executor."""
    if tool_name == "query_crm":
        return _exec_query_crm(
            db=db,
            tenant_id=tenant_id,
            entity_type=tool_args.get("entity_type", "organization"),
            search_term=tool_args.get("search_term", ""),
            filters=tool_args.get("filters"),
            limit=tool_args.get("limit", 10),
        )
    elif tool_name == "get_pipeline_stats":
        return _exec_get_pipeline_stats(db=db, tenant_id=tenant_id)
    elif tool_name == "get_account_details":
        return _exec_get_account_details(
            db=db,
            tenant_id=tenant_id,
            account_name=tool_args.get("account_name", ""),
        )
    elif tool_name == "search_web":
        return _exec_search_web(query=tool_args.get("query", ""))
    elif tool_name == "get_recent_activities":
        return _exec_get_recent_activities(
            db=db,
            tenant_id=tenant_id,
            days=tool_args.get("days", 7),
        )
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ── Main Agentic Chat Function ───────────────────────────────

def workspace_chat(
    user_message: str,
    conversation_history: list[dict],
    tenant_id: str,
    user_id: str = "",
    user_email: str = "",
) -> tuple[str, list[dict]]:
    """Agentic CRM chat for workspace mode.

    Uses Kimi K2 via Groq with tool-calling to query CRM data,
    search the web, and synthesize contextual responses.

    Args:
        user_message: The user's current message.
        conversation_history: Previous messages [{role, content}].
        tenant_id: Tenant ID for CRM scoping.
        user_id: User ID for context.
        user_email: User email for context.

    Returns:
        Tuple of (response_text, tool_steps_list).
    """
    from app.infrastructure.database import SessionLocal

    db = SessionLocal()
    tool_steps: list[dict] = []

    try:
        # ── Build context ────────────────────────────────────
        org_context = load_advisor_context(db=db, tenant_id=tenant_id, user_id=user_id)
        crm_context = load_crm_context(db=db, tenant_id=tenant_id, user_id=user_id)

        system_prompt = WORKSPACE_SYSTEM_PROMPT.replace(
            "{org_context}", org_context
        ).replace(
            "{crm_context}", crm_context
        )

        # ── Build messages ───────────────────────────────────
        messages: list[dict] = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 20 messages)
        for msg in conversation_history[-20:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })

        messages.append({"role": "user", "content": user_message})

        # ── Agentic loop ─────────────────────────────────────
        client = Groq(api_key=settings.groq_api_key)

        for round_num in range(MAX_TOOL_ROUNDS):
            logger.info(
                "workspace_llm_call",
                round=round_num,
                messages_count=len(messages),
            )

            response = client.chat.completions.create(
                model=settings.workspace_model,
                messages=messages,
                tools=CRM_TOOLS,
                tool_choice="auto",
                temperature=settings.workspace_temperature,
                max_tokens=settings.workspace_max_tokens,
            )

            choice = response.choices[0]
            message = choice.message

            # If no tool calls → we have the final response
            if not message.tool_calls:
                content = message.content or ""
                logger.info(
                    "workspace_response",
                    rounds=round_num + 1,
                    tools_called=len(tool_steps),
                    response_length=len(content),
                    tokens_in=response.usage.prompt_tokens if response.usage else 0,
                    tokens_out=response.usage.completion_tokens if response.usage else 0,
                )
                return content, tool_steps

            # Process tool calls
            # Add assistant message with tool calls to conversation
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            for tc in message.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

                logger.info(
                    "workspace_tool_call",
                    tool=tool_name,
                    args=tool_args,
                    round=round_num,
                )

                # Execute the tool
                result = _execute_tool(
                    tool_name=tool_name,
                    tool_args=tool_args,
                    db=db,
                    tenant_id=tenant_id,
                )

                tool_steps.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "status": "done",
                })

                # Add tool result to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        # If we exhausted rounds, return whatever we have
        logger.warning("workspace_max_rounds", rounds=MAX_TOOL_ROUNDS)
        return (
            "J'ai effectué plusieurs recherches mais je n'ai pas pu finaliser "
            "l'analyse. Pouvez-vous reformuler votre question?",
            tool_steps,
        )

    except Exception as e:
        logger.error("workspace_agent_error", error=str(e))
        return (
            f"⚠️ Une erreur est survenue dans le mode workspace: {str(e)[:200]}",
            tool_steps,
        )

    finally:
        db.close()
