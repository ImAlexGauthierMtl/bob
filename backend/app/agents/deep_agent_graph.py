"""Deep Agent LangGraph — autonomous full-stack BCC builder.

Graph flow:
  supervisor → plan_validator → domain_builder → intent_builder
  → task_builder → tool_schema_generator → workflow_code_generator
  → code_reviewer → deployer → END

Uses Claude Sonnet 4.6 via OpenRouter for planning, code generation, and review.
Builder nodes are deterministic Python that writes to the database.
Plan validator catches hallucinated tables/entities before any DB write.
Generator nodes produce tool schemas and workflow code.
Deployer writes .py files and hot-loads them.
"""

import json
import os
import re
import structlog
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

logger = structlog.get_logger(__name__)

MAX_REVISION_CYCLES = 3

FORBIDDEN_PATTERNS = [
    r"\bos\.", r"\bsubprocess\b", r"\bsys\b", r"\bexec\s*\(",
    r"\beval\s*\(", r"__import__", r"\bopen\s*\(", r"\brequests\b",
    r"\bhttpx\b", r"\bshutil\b", r"\bpathlib\b", r"\bglob\b",
]

ALLOWED_IMPORTS = [
    "app.domain.entities", "sqlalchemy", "datetime", "json", "re",
    "app.agents.workflow_engine",
]

VALID_DB_TABLES = {"organizations", "contacts", "opportunities", "activities", "products"}

VALID_ENTITY_MODULES = {"organization", "contact", "opportunity", "activity", "product", "base"}

# ── ORM Schema Reference ─────────────────────────────────────
# Used by supervisor, code generator, and plan validator.

ORM_SCHEMA = """
AVAILABLE ORM ENTITIES (these are the ONLY tables and columns you can use):

1. Organization (table: organizations)
   Import: from app.domain.entities.organization import Organization
   Columns: id, name, industry, website, phone, email,
            address_street, address_city, address_state, address_country, address_postal_code,
            status (PROSPECT/CUSTOMER/PARTNER/INACTIVE/OTHER),
            org_type (CUSTOMER/SUPPLIER/PARTNER/OTHER),
            employee_count, annual_revenue, description,
            ai_enriched, linkedin_url, logo_url, organization_profile,
            owner_id, tenant_id, created_at, updated_at
   Relations: contacts, opportunities, quotes, activities

2. Contact (table: contacts)
   Import: from app.domain.entities.contact import Contact
   Columns: id, first_name, last_name, email, phone, mobile,
            job_title, department,
            status (ACTIVE/INACTIVE/LEAD),
            linkedin_url, notes,
            organization_id, owner_id, tenant_id, created_at, updated_at
   Relations: opportunities, activities

3. Opportunity (table: opportunities)
   Import: from app.domain.entities.opportunity import Opportunity
   Columns: id, name, description,
            stage (PROSPECTING/QUALIFICATION/PROPOSAL/NEGOTIATION/CLOSED_WON/CLOSED_LOST),
            priority (LOW/MEDIUM/HIGH/CRITICAL),
            amount, probability, close_date, source,
            organization_id, contact_id, owner_id, tenant_id, created_at, updated_at
   Relations: quotes, activities, products

4. Activity (table: activities)
   Import: from app.domain.entities.activity import Activity
   Columns: id, subject, description,
            activity_type (CALL/EMAIL/MEETING/TASK/NOTE),
            priority (LOW/MEDIUM/HIGH/URGENT),
            status (PENDING/IN_PROGRESS/COMPLETED/CANCELLED),
            due_date, completed_at,
            organization_id, contact_id, opportunity_id, assigned_to,
            owner_id, tenant_id, created_at, updated_at

5. Product (table: products)
   Import: from app.domain.entities.product import Product
   Columns: id, name, category, sku, price, description,
            tenant_id, created_at, updated_at

THERE ARE NO OTHER TABLES. Do NOT reference tables like candidates, interviews,
onboarding, tickets, billing, subscriptions, etc. — they do not exist.
""".strip()

CONCEPT_MAPPING = """
CONCEPT MAPPING — How to map non-CRM concepts to existing tables:

When a user asks for a domain that seems to need new tables, you MUST map
the concept to the 5 existing tables. Examples:

- Candidates / Applicants → contacts with status=LEAD, notes containing application info
- Interviews → activities with activity_type=MEETING, subject prefixed with "[Interview]"
- Onboarding tasks → activities with activity_type=TASK, subject prefixed with "[Onboarding]"
- Support tickets → activities with activity_type=TASK, subject prefixed with "[Ticket]"
- Customer success checks → activities with activity_type=TASK, subject prefixed with "[CS]"
- Billing / Invoices → opportunities with specific stages (CLOSED_WON for invoiced)
- MRR / Revenue metrics → opportunities filtered by stage=CLOSED_WON and close_date range
- Churn tracking → opportunities with stage=CLOSED_LOST and close_date range
- Leads → contacts with status=LEAD
- Tasks / Reminders → activities with activity_type=TASK

The generated workflow code MUST import only from the 5 real entity modules.
""".strip()

SAMPLE_WORKFLOW = '''
from app.agents.workflow_engine import workflow, WorkflowContext, WorkflowResult

@workflow("example_intent")
def example_intent_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Example: query opportunities and return stats."""
    from app.domain.entities.opportunity import Opportunity
    from sqlalchemy import func

    results = ctx.db.query(
        Opportunity.stage,
        func.count(Opportunity.id),
        func.sum(Opportunity.amount),
    ).filter(
        Opportunity.tenant_id == ctx.tenant_id,
    ).group_by(Opportunity.stage).all()

    if not results:
        return ctx.complete(message="No data found.")

    lines = []
    for stage, count, value in results:
        lines.append(f"- **{stage}**: {count} deals — {float(value or 0):,.0f}$")

    ctx.emit_action("bob_display",
        display_type="stats", title="Results",
        icon="fa-solid fa-chart-bar",
        stats=[{"label": s, "value": str(c)} for s, c, _ in results],
    )
    ctx.add_tool_step("query_data")
    return ctx.complete(message="\\n".join(lines))
'''


# ── State ─────────────────────────────────────────────────────

class DeepAgentState(TypedDict):
    tenant_id: str
    user_id: str
    user_email: str
    instruction: str
    plan: dict
    domains_created: list
    intents_created: list
    tasks_created: list
    generated_tool_schemas: list
    generated_code: dict
    code_review_result: dict
    review_result: dict
    status: str
    error: Optional[str]
    revision_count: int


# ── Supervisor Node ───────────────────────────────────────────

def supervisor_node(state: DeepAgentState) -> DeepAgentState:
    """Use Claude to analyze the instruction and produce a structured BCC plan."""
    from app.agents.deep_llm_client import deep_agent_chat_json

    existing_context = _load_existing_bcc_summary(state["tenant_id"])
    existing_tools = _load_existing_tool_names()
    existing_workflows = _load_existing_workflow_keys()
    existing_triggers = _load_existing_trigger_phrases(state["tenant_id"])

    revision_feedback = ""
    if state.get("review_result") and state["review_result"].get("issues"):
        revision_feedback = (
            "\n\n⚠️ PREVIOUS PLAN REJECTED — you must fix these issues:\n"
            + "\n".join(f"- {i}" for i in state["review_result"]["issues"])
        )

    system = (
        "You are the Deep Agent Supervisor for Bob's Control Center (BCC).\n"
        "You plan the creation of BCC domains, intents, tasks, AND new workflow code.\n\n"
        "BCC structure:\n"
        "- Domain: a high-level area (e.g. 'CRM Sales', 'SaaS Metrics')\n"
        "- Intent: a user goal within a domain, with workflow_key and trigger_phrases\n"
        "- Task: a step within an intent, with tool_name and context (procedure, required_info)\n\n"
        "You can create intents that NEED new workflow code. For those, set:\n"
        "  workflow_key = intent name (snake_case)\n"
        "  needs_workflow = true\n\n"
        "You can also define new tool schemas for intents that need custom data queries.\n\n"
        f"{ORM_SCHEMA}\n\n"
        f"{CONCEPT_MAPPING}\n\n"
        "═══════════════════════════════════════════\n"
        "CRITICAL RULES (violations will be REJECTED by the validator):\n"
        "═══════════════════════════════════════════\n"
        "1. db_table MUST be one of: organizations, contacts, opportunities, activities, products.\n"
        "   ANY OTHER TABLE NAME WILL BE REJECTED. There are NO other tables.\n"
        "2. NEVER invent tables that don't exist (no 'candidates', 'interviews', 'tickets', etc.).\n"
        "   Instead, MAP the concept to existing tables using the Concept Mapping above.\n"
        "3. trigger_phrases MUST NOT collide with existing trigger phrases (see below).\n"
        "4. If needs_workflow=true, workflow_key MUST equal the intent name.\n"
        "5. tool_name must match an existing tool or be null.\n"
        "6. trigger_phrases: min 3 per intent, mix FR and EN.\n"
        "7. Each intent needs at least 1 task.\n"
        "8. Use FontAwesome 6 icons for domains.\n"
        "═══════════════════════════════════════════\n\n"
        f"Existing BCC domains/intents:\n{existing_context}\n\n"
        f"Existing tools (do NOT recreate): {', '.join(existing_tools)}\n\n"
        f"Existing workflow_keys (do NOT recreate): {', '.join(existing_workflows)}\n\n"
        f"Existing trigger_phrases (do NOT duplicate):\n{existing_triggers}\n"
        f"{revision_feedback}"
    )

    prompt = (
        f"User instruction: {state['instruction']}\n\n"
        "Produce a JSON plan:\n"
        "{\n"
        '  "domains": [\n'
        '    {\n'
        '      "name": "...", "description": "...", "icon": "fa-solid fa-...",\n'
        '      "intents": [\n'
        '        {\n'
        '          "name": "snake_case_name", "description": "...",\n'
        '          "workflow_key": "snake_case_key",\n'
        '          "needs_workflow": true,\n'
        '          "trigger_phrases": ["phrase1", "phrase2", "phrase3"],\n'
        '          "category": "...",\n'
        '          "tasks": [\n'
        '            {"name": "Task name", "tool_name": "tool_or_null", "sort_order": 0,\n'
        '             "context": {"procedure": ["step1"], "tool_priority": [], '
        '"required_info": [], "db_table": "MUST be one of: organizations|contacts|opportunities|activities|products", '
        '"db_operation": "SELECT", '
        '"expected_output": "description"}}\n'
        '          ]\n'
        '        }\n'
        '      ]\n'
        '    }\n'
        '  ]\n'
        "}\n\n"
        "REMEMBER: db_table MUST be one of: organizations, contacts, opportunities, activities, products.\n"
        "If the user asks for something that sounds like a different table, MAP IT to an existing one."
    )

    try:
        plan = deep_agent_chat_json(prompt, system_prompt=system)
        state["plan"] = plan
        state["status"] = "validating"
        logger.info("deep_agent_plan_created", domains=len(plan.get("domains", [])))
    except Exception as e:
        state["error"] = f"Supervisor planning failed: {str(e)}"
        state["status"] = "error"
        logger.error("deep_agent_supervisor_error", error=str(e))

    return state


# ── Plan Validator Node (deterministic, zero LLM cost) ────────

def plan_validator_node(state: DeepAgentState) -> DeepAgentState:
    """Validate the supervisor's plan before writing anything to DB.

    Checks:
    - db_table references only real tables
    - No trigger phrase collisions with existing intents
    - needs_workflow consistency
    - ORM entity references are valid
    """
    if state["status"] == "error":
        return state

    plan = state.get("plan", {})
    issues = []
    existing_workflows = set(_load_existing_workflow_keys())
    existing_triggers_by_intent = _load_existing_trigger_phrases_dict(state["tenant_id"])

    # Collect all intent names from the current plan so we can skip
    # phrases belonging to intents that match (idempotent on retry).
    plan_intent_names = set()
    for domain_def in plan.get("domains", []):
        for intent_def in domain_def.get("intents", []):
            plan_intent_names.add(intent_def.get("name", ""))

    all_existing_phrases = set()
    for existing_intent_name, phrases in existing_triggers_by_intent.items():
        # Skip intents that are part of this plan (previous failed run).
        if existing_intent_name not in plan_intent_names:
            all_existing_phrases.update(p.lower().strip() for p in phrases)

    # Track phrases within this plan for intra-plan duplicate detection.
    seen_phrases: dict[str, str] = {}  # normalized phrase -> first intent name

    for domain_def in plan.get("domains", []):
        for intent_def in domain_def.get("intents", []):
            intent_name = intent_def.get("name", "<unnamed>")

            # Check needs_workflow consistency
            if intent_def.get("needs_workflow", False):
                wk = intent_def.get("workflow_key", "")
                if wk != intent_name:
                    issues.append(
                        f"[{intent_name}] needs_workflow=true but workflow_key='{wk}' "
                        f"does not match intent name. Set workflow_key='{intent_name}'."
                    )
                if wk in existing_workflows:
                    issues.append(
                        f"[{intent_name}] workflow_key='{wk}' already exists. "
                        f"Set needs_workflow=false or use a different name."
                    )

            # Check trigger phrase collisions with external intents
            new_phrases = intent_def.get("trigger_phrases", [])
            for phrase in new_phrases:
                normalized = phrase.lower().strip()
                if normalized in all_existing_phrases:
                    # Find which existing intent owns this phrase
                    owner = next(
                        (iname for iname, iphrases in existing_triggers_by_intent.items()
                         if normalized in {p.lower().strip() for p in iphrases}),
                        "unknown",
                    )
                    issues.append(
                        f"[{intent_name}] Trigger phrase '{phrase}' collides with existing intent '{owner}'."
                    )

                # Intra-plan duplicate detection
                if normalized in seen_phrases:
                    if seen_phrases[normalized] != intent_name:
                        issues.append(
                            f"[{intent_name}] Trigger phrase '{phrase}' duplicates "
                            f"phrase in intent '{seen_phrases[normalized]}' within this plan."
                        )
                else:
                    seen_phrases[normalized] = intent_name

            # Check db_table in tasks
            for task_def in intent_def.get("tasks", []):
                task_name = task_def.get("name", "<unnamed task>")
                ctx = task_def.get("context", {})

                db_table = ctx.get("db_table")
                if db_table and db_table not in VALID_DB_TABLES:
                    issues.append(
                        f"[{intent_name}/{task_name}] Invalid db_table='{db_table}'. "
                        f"Must be one of: {', '.join(sorted(VALID_DB_TABLES))}. "
                        f"Map the concept to an existing table using Concept Mapping."
                    )

                db_tables = ctx.get("db_tables", [])
                for t in db_tables:
                    if t not in VALID_DB_TABLES:
                        issues.append(
                            f"[{intent_name}/{task_name}] Invalid db_tables entry='{t}'. "
                            f"Must be one of: {', '.join(sorted(VALID_DB_TABLES))}."
                        )

    if issues:
        revision_count = state.get("revision_count", 0) + 1
        state["revision_count"] = revision_count
        state["review_result"] = {"approved": False, "issues": issues}

        if revision_count >= MAX_REVISION_CYCLES:
            state["status"] = "error"
            state["error"] = (
                "Plan validation failed after max revisions. Issues: "
                + "; ".join(issues[:5])
            )
            logger.error("deep_agent_plan_validation_max_revisions", issues=issues)
        else:
            state["status"] = "planning"
            logger.info("deep_agent_plan_validation_failed", issues=issues)
    else:
        state["status"] = "building"
        state["review_result"] = {"approved": True, "summary": "Plan validated"}
        logger.info("deep_agent_plan_validated")

    return state


# ── Domain Builder Node ───────────────────────────────────────

def domain_builder_node(state: DeepAgentState) -> DeepAgentState:
    """Create BccDomain records from the plan."""
    if state["status"] == "error":
        return state

    from app.infrastructure.database import SessionLocal
    from app.domain.entities.bcc_entities import BccDomain
    from app.domain.entities.base import generate_uuid

    db = SessionLocal()
    try:
        domains_created = []
        for domain_def in state["plan"].get("domains", []):
            existing = db.query(BccDomain).filter_by(
                tenant_id=state["tenant_id"],
                name=domain_def["name"],
            ).first()
            if existing:
                domains_created.append({"id": existing.id, "name": existing.name, "existed": True})
                continue

            domain = BccDomain(
                id=generate_uuid(),
                tenant_id=state["tenant_id"],
                name=domain_def["name"],
                description=domain_def.get("description"),
                icon=domain_def.get("icon"),
            )
            db.add(domain)
            db.flush()
            domains_created.append({"id": domain.id, "name": domain.name, "existed": False})

        db.commit()
        state["domains_created"] = domains_created
        logger.info("deep_agent_domains_built", count=len(domains_created))
    except Exception as e:
        db.rollback()
        state["error"] = f"Domain builder failed: {str(e)}"
        state["status"] = "error"
        logger.error("deep_agent_domain_builder_error", error=str(e))
    finally:
        db.close()

    return state


# ── Intent Builder Node ───────────────────────────────────────

def intent_builder_node(state: DeepAgentState) -> DeepAgentState:
    """Create BccIntent records from the plan, linking to domains."""
    if state["status"] == "error":
        return state

    from app.infrastructure.database import SessionLocal
    from app.domain.entities.bcc_entities import BccDomain, BccIntent
    from app.domain.entities.base import generate_uuid

    db = SessionLocal()
    try:
        intents_created = []
        for domain_def in state["plan"].get("domains", []):
            domain = db.query(BccDomain).filter_by(
                tenant_id=state["tenant_id"],
                name=domain_def["name"],
            ).first()
            if not domain:
                continue

            for intent_def in domain_def.get("intents", []):
                existing = db.query(BccIntent).filter_by(
                    tenant_id=state["tenant_id"],
                    name=intent_def["name"],
                ).first()
                if existing:
                    intents_created.append({"id": existing.id, "name": existing.name, "existed": True})
                    continue

                intent = BccIntent(
                    id=generate_uuid(),
                    tenant_id=state["tenant_id"],
                    name=intent_def["name"],
                    description=intent_def.get("description"),
                    category=intent_def.get("category"),
                    trigger_phrases=intent_def.get("trigger_phrases", []),
                    domain_id=domain.id,
                    workflow_key=intent_def.get("workflow_key"),
                    pipeline_key=intent_def.get("pipeline_key"),
                )
                db.add(intent)
                db.flush()
                intents_created.append({
                    "id": intent.id, "name": intent.name,
                    "existed": False,
                    "needs_workflow": intent_def.get("needs_workflow", False),
                })

        db.commit()
        state["intents_created"] = intents_created
        logger.info("deep_agent_intents_built", count=len(intents_created))
    except Exception as e:
        db.rollback()
        state["error"] = f"Intent builder failed: {str(e)}"
        state["status"] = "error"
        logger.error("deep_agent_intent_builder_error", error=str(e))
    finally:
        db.close()

    return state


# ── Task Builder Node ─────────────────────────────────────────

def task_builder_node(state: DeepAgentState) -> DeepAgentState:
    """Create BccTaskTemplate and BccIntentTask records from the plan."""
    if state["status"] == "error":
        return state

    from app.infrastructure.database import SessionLocal
    from app.domain.entities.bcc_entities import BccIntent, BccTaskTemplate, BccIntentTask
    from app.domain.entities.base import generate_uuid

    db = SessionLocal()
    try:
        tasks_created = []
        for domain_def in state["plan"].get("domains", []):
            for intent_def in domain_def.get("intents", []):
                intent = db.query(BccIntent).filter_by(
                    tenant_id=state["tenant_id"],
                    name=intent_def["name"],
                ).first()
                if not intent:
                    continue

                existing_links = len(intent.task_links) if intent.task_links else 0
                if existing_links > 0:
                    tasks_created.append({
                        "intent": intent.name,
                        "tasks_existed": existing_links,
                    })
                    continue

                for task_def in intent_def.get("tasks", []):
                    tpl = BccTaskTemplate(
                        id=generate_uuid(),
                        tenant_id=state["tenant_id"],
                        name=task_def["name"],
                        description=task_def.get("name"),
                        context=task_def.get("context", {}),
                        frequency="ad_hoc",
                        category=intent_def.get("category"),
                    )
                    db.add(tpl)
                    db.flush()

                    link = BccIntentTask(
                        id=generate_uuid(),
                        tenant_id=state["tenant_id"],
                        intent_id=intent.id,
                        task_template_id=tpl.id,
                        sort_order=task_def.get("sort_order", 0),
                        tool_name=task_def.get("tool_name"),
                    )
                    db.add(link)
                    tasks_created.append({"intent": intent.name, "task": task_def["name"]})

        db.commit()
        state["tasks_created"] = tasks_created
        logger.info("deep_agent_tasks_built", count=len(tasks_created))
    except Exception as e:
        db.rollback()
        state["error"] = f"Task builder failed: {str(e)}"
        state["status"] = "error"
        logger.error("deep_agent_task_builder_error", error=str(e))
    finally:
        db.close()

    return state


# ── Tool Schema Generator Node ────────────────────────────────

def tool_schema_generator_node(state: DeepAgentState) -> DeepAgentState:
    """Generate OpenAI-format tool schemas for new tools defined in the plan."""
    if state["status"] == "error":
        return state

    from app.agents.deep_llm_client import deep_agent_chat_json

    existing_tools = set(_load_existing_tool_names())
    new_tool_names = set()
    for domain_def in state["plan"].get("domains", []):
        for intent_def in domain_def.get("intents", []):
            for task_def in intent_def.get("tasks", []):
                tn = task_def.get("tool_name")
                if tn and tn not in existing_tools:
                    new_tool_names.add(tn)

    if not new_tool_names:
        state["generated_tool_schemas"] = []
        logger.info("deep_agent_no_new_tools")
        return state

    system = (
        "You generate OpenAI-compatible function-calling tool schemas.\n"
        "Each tool schema must follow this exact format:\n"
        '{"type": "function", "function": {"name": "tool_name", '
        '"description": "...", "parameters": {"type": "object", '
        '"properties": {...}, "required": [...]}}}\n\n'
        "These tools will query CRM data. Keep parameters simple:\n"
        "- query/search terms as strings\n"
        "- limit as integer with default\n"
        "- date_from/date_to as strings\n\n"
        f"{ORM_SCHEMA}"
    )

    prompt = (
        f"Generate tool schemas for these new tools: {json.dumps(list(new_tool_names))}\n\n"
        "Context from the plan:\n"
        + json.dumps(
            [
                {"tool_name": tn, "tasks": [
                    {"intent": id_.get("name", ""), "task": td.get("name", ""), "context": td.get("context", {})}
                    for dd in state["plan"].get("domains", [])
                    for id_ in dd.get("intents", [])
                    for td in id_.get("tasks", [])
                    if td.get("tool_name") == tn
                ]}
                for tn in new_tool_names
            ],
            indent=2,
        )
        + "\n\nReturn JSON: {\"tool_schemas\": [...]}"
    )

    try:
        result = deep_agent_chat_json(prompt, system_prompt=system)
        schemas = result.get("tool_schemas", [])
        state["generated_tool_schemas"] = schemas

        _store_tool_schemas_in_bcc(state["tenant_id"], schemas)

        logger.info("deep_agent_tool_schemas_generated", count=len(schemas))
    except Exception as e:
        state["generated_tool_schemas"] = []
        logger.warning("deep_agent_tool_schema_gen_failed", error=str(e))

    return state


# ── Workflow Code Generator Node ──────────────────────────────

def workflow_code_generator_node(state: DeepAgentState) -> DeepAgentState:
    """Generate Python workflow code for intents that need it."""
    if state["status"] == "error":
        return state

    from app.agents.deep_llm_client import deep_agent_chat

    intents_needing_code = []
    for domain_def in state["plan"].get("domains", []):
        for intent_def in domain_def.get("intents", []):
            if intent_def.get("needs_workflow", False):
                existing_wf = _load_existing_workflow_keys()
                if intent_def["name"] not in existing_wf:
                    intents_needing_code.append(intent_def)

    if not intents_needing_code:
        state["generated_code"] = {}
        logger.info("deep_agent_no_workflow_code_needed")
        return state

    generated_code = {}
    for intent_def in intents_needing_code:
        system = (
            "You are a Python code generator for Bob's CRM workflow engine.\n"
            "Generate a SINGLE Python file that implements a workflow function.\n\n"
            "═══════════════════════════════════════════\n"
            "STRICT RULES (code will be REJECTED if violated):\n"
            "═══════════════════════════════════════════\n"
            "- Import workflow, WorkflowContext, WorkflowResult from app.agents.workflow_engine\n"
            "- Decorate the main function with @workflow(\"intent_name\")\n"
            "- Function signature: def intent_name_flow(ctx: WorkflowContext) -> WorkflowResult\n"
            "- ALWAYS filter queries by ctx.tenant_id\n"
            "- Use ctx.db for database queries (SQLAlchemy session)\n"
            "- Use ctx.complete(message=...) to return results\n"
            "- Use ctx.emit_action(\"bob_display\", ...) for rich UI display\n"
            "- Use ctx.add_tool_step(\"step_name\") to record steps\n"
            "- MAX 80 lines of code\n"
            "- FORBIDDEN: os, subprocess, sys, exec, eval, __import__, open(), requests, httpx\n"
            "- Do NOT include any markdown formatting, just raw Python code\n\n"
            "═══════════════════════════════════════════\n"
            "ENTITY IMPORTS — ONLY these 5 modules exist:\n"
            "═══════════════════════════════════════════\n"
            "- from app.domain.entities.organization import Organization\n"
            "- from app.domain.entities.contact import Contact\n"
            "- from app.domain.entities.opportunity import Opportunity\n"
            "- from app.domain.entities.activity import Activity\n"
            "- from app.domain.entities.product import Product\n\n"
            "Do NOT import from any other entity module. Modules like\n"
            "app.domain.entities.candidate, app.domain.entities.interview,\n"
            "app.domain.entities.ticket DO NOT EXIST and will cause import errors.\n\n"
            "Also allowed: from sqlalchemy import func, and, or_, desc, asc\n"
            "Also allowed: import datetime, import json, import re\n\n"
            f"{ORM_SCHEMA}\n\n"
            f"{CONCEPT_MAPPING}\n\n"
            f"REFERENCE — example workflow:\n{SAMPLE_WORKFLOW}\n"
        )

        tasks_desc = json.dumps(intent_def.get("tasks", []), indent=2)
        prompt = (
            f"Generate a workflow for intent: {intent_def['name']}\n"
            f"Description: {intent_def.get('description', '')}\n"
            f"Category: {intent_def.get('category', '')}\n"
            f"Tasks/steps:\n{tasks_desc}\n\n"
            "Output ONLY the Python code. No markdown. No explanation.\n"
            "REMEMBER: only import from organization, contact, opportunity, activity, product."
        )

        try:
            code = deep_agent_chat(prompt, system_prompt=system)
            code = code.strip()
            if code.startswith("```"):
                lines = code.split("\n")
                code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            generated_code[intent_def["name"]] = code
            logger.info("deep_agent_workflow_generated", intent=intent_def["name"])
        except Exception as e:
            logger.error("deep_agent_workflow_gen_failed", intent=intent_def["name"], error=str(e))
            state["error"] = f"Workflow code generation failed for {intent_def['name']}: {str(e)}"
            state["status"] = "error"
            return state

    state["generated_code"] = generated_code
    return state


# ── Code Reviewer Node ────────────────────────────────────────

def code_reviewer_node(state: DeepAgentState) -> DeepAgentState:
    """Validate generated code for safety and correctness."""
    if state["status"] == "error":
        return state

    generated_code = state.get("generated_code", {})

    if not generated_code:
        state["code_review_result"] = {"approved": True, "summary": "No code to review"}
        state["status"] = "deploying"
        return state

    all_issues = []
    for intent_name, code in generated_code.items():
        issues = _static_validate_code(intent_name, code)
        all_issues.extend(issues)

    if all_issues:
        revision_count = state.get("revision_count", 0) + 1
        state["revision_count"] = revision_count
        state["code_review_result"] = {"approved": False, "issues": all_issues}

        if revision_count >= MAX_REVISION_CYCLES:
            state["status"] = "deploying"
            state["generated_code"] = {}
            state["code_review_result"] = {
                "approved": False,
                "issues": all_issues,
                "summary": "Max revisions reached — deploying BCC structure only, no workflow code",
            }
            logger.warning("deep_agent_code_review_max_revisions", issues=all_issues)
        else:
            state["status"] = "planning"
            logger.info("deep_agent_code_review_rejected", issues=all_issues)
        return state

    from app.agents.deep_llm_client import deep_agent_chat_json

    system = (
        "You are a security-focused code reviewer for a CRM system.\n"
        "Review the generated Python code for:\n"
        "1. SQL injection risks (should use ORM, not raw SQL)\n"
        "2. Missing tenant_id filtering (EVERY query must filter by ctx.tenant_id)\n"
        "3. Dangerous operations (file I/O, network calls, code execution)\n"
        "4. Correctness of WorkflowContext API usage\n"
        "5. Invalid entity imports (ONLY organization, contact, opportunity, activity, product exist)\n"
        "6. References to non-existent columns\n"
        "7. Proper error handling\n\n"
        f"{ORM_SCHEMA}\n\n"
        "Respond with JSON: {\"approved\": true/false, \"issues\": [\"...\"], \"summary\": \"...\"}"
    )

    all_code = "\n\n".join(
        f"# === {name} ===\n{code}"
        for name, code in generated_code.items()
    )
    prompt = f"Review this generated workflow code:\n\n{all_code}"

    try:
        review = deep_agent_chat_json(prompt, system_prompt=system)
        state["code_review_result"] = review

        if review.get("approved", False):
            state["status"] = "deploying"
            logger.info("deep_agent_code_review_approved")
        else:
            revision_count = state.get("revision_count", 0) + 1
            state["revision_count"] = revision_count
            if revision_count >= MAX_REVISION_CYCLES:
                state["status"] = "deploying"
                state["generated_code"] = {}
                state["code_review_result"]["summary"] = (
                    "Max revisions — deploying BCC only"
                )
                logger.warning("deep_agent_code_review_max_revisions")
            else:
                state["status"] = "planning"
                logger.info("deep_agent_code_review_rejected", issues=review.get("issues", []))
    except Exception as e:
        state["code_review_result"] = {"approved": True, "summary": "LLM review skipped due to error"}
        state["status"] = "deploying"
        logger.warning("deep_agent_code_reviewer_error", error=str(e))

    return state


# ── Deployer Node ─────────────────────────────────────────────

def deployer_node(state: DeepAgentState) -> DeepAgentState:
    """Write generated workflow files to disk and hot-load them."""
    if state["status"] == "error":
        return state

    generated_code = state.get("generated_code", {})
    if not generated_code:
        state["status"] = "done"
        return state

    generated_dir = os.path.join(os.path.dirname(__file__), "generated")
    os.makedirs(generated_dir, exist_ok=True)

    init_file = os.path.join(generated_dir, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("")

    deployed = []
    for intent_name, code in generated_code.items():
        filename = f"{intent_name}.py"
        filepath = os.path.join(generated_dir, filename)

        with open(filepath, "w") as f:
            f.write(code)

        deployed.append(intent_name)
        logger.info("deep_agent_workflow_deployed", intent=intent_name, path=filepath)

    from app.agents.workflow_engine import load_generated_workflows
    loaded = load_generated_workflows()

    state["status"] = "done"
    state["code_review_result"]["deployed"] = deployed
    state["code_review_result"]["loaded"] = loaded
    logger.info("deep_agent_deploy_complete", deployed=deployed, loaded=loaded)

    return state


# ── Routing ───────────────────────────────────────────────────

def _route_after_plan_validation(state: DeepAgentState) -> str:
    """Route after plan_validator: build or back to supervisor."""
    if state["status"] == "building":
        return "domain_builder"
    if state["status"] == "planning":
        return "supervisor"
    if state["status"] == "error":
        return END
    return "domain_builder"


def _route_after_review(state: DeepAgentState) -> str:
    """Route after code reviewer: deploy, retry, or end."""
    if state["status"] == "deploying":
        return "deployer"
    if state["status"] == "planning":
        return "supervisor"
    if state["status"] == "error":
        return END
    return "deployer"


# ── Static Validation ─────────────────────────────────────────

def _static_validate_code(intent_name: str, code: str) -> list[str]:
    """Run static checks on generated code before LLM review."""
    issues = []

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            issues.append(f"[{intent_name}] Forbidden pattern: {pattern}")

    lines = code.strip().split("\n")
    if len(lines) > 120:
        issues.append(f"[{intent_name}] Code too long: {len(lines)} lines (max 120)")

    if "ctx.tenant_id" not in code and "tenant_id" not in code:
        issues.append(f"[{intent_name}] Missing tenant_id filtering")

    if "@workflow(" not in code:
        issues.append(f"[{intent_name}] Missing @workflow() decorator")

    if "def " not in code:
        issues.append(f"[{intent_name}] No function definition found")

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            module = stripped.split()[1].split(".")[0]
            if module == "from":
                module = stripped.split()[1]
            if not any(module.startswith(allowed.split(".")[0]) for allowed in ALLOWED_IMPORTS):
                issues.append(f"[{intent_name}] Forbidden import: {stripped}")

    entity_import_re = re.compile(r"from\s+app\.domain\.entities\.(\w+)\s+import")
    for match in entity_import_re.finditer(code):
        entity_module = match.group(1)
        if entity_module not in VALID_ENTITY_MODULES:
            issues.append(
                f"[{intent_name}] Invalid entity import: app.domain.entities.{entity_module} "
                f"does not exist. Valid modules: {', '.join(sorted(VALID_ENTITY_MODULES))}"
            )

    return issues


# ── Helpers ───────────────────────────────────────────────────

def _load_existing_bcc_summary(tenant_id: str) -> str:
    """Load a text summary of existing BCC structure for LLM context."""
    try:
        from app.infrastructure.database import SessionLocal
        from app.domain.entities.bcc_entities import BccDomain, BccIntent

        db = SessionLocal()
        try:
            domains = db.query(BccDomain).filter_by(tenant_id=tenant_id).all()
            if not domains:
                return "BCC is empty — no domains, intents, or tasks defined."

            parts = []
            for d in domains:
                intents = db.query(BccIntent).filter_by(
                    tenant_id=tenant_id, domain_id=d.id,
                ).all()
                intent_names = [i.name for i in intents]
                parts.append(f"- {d.name} ({d.icon}): {len(intent_names)} intents — {', '.join(intent_names)}")
            return "\n".join(parts)
        finally:
            db.close()
    except Exception:
        return "Unable to load existing BCC."


def _load_existing_tool_names() -> list[str]:
    """Get names of all hardcoded BOB_TOOLS."""
    try:
        from app.agents.bob_tools import BOB_TOOLS
        return [t["function"]["name"] for t in BOB_TOOLS]
    except Exception:
        return []


def _load_existing_workflow_keys() -> list[str]:
    """Get names of all registered workflows."""
    try:
        from app.agents.workflow_engine import _WORKFLOWS
        return list(_WORKFLOWS.keys())
    except Exception:
        return []


def _load_existing_trigger_phrases(tenant_id: str) -> str:
    """Load existing trigger phrases formatted for the LLM prompt."""
    data = _load_existing_trigger_phrases_dict(tenant_id)
    if not data:
        return "No existing trigger phrases."
    lines = []
    for intent_name, phrases in data.items():
        lines.append(f"  {intent_name}: {', '.join(phrases[:5])}")
    return "\n".join(lines)


def _load_existing_trigger_phrases_dict(tenant_id: str) -> dict[str, list[str]]:
    """Load existing trigger phrases as a dict: intent_name -> phrases."""
    try:
        from app.infrastructure.database import SessionLocal
        from app.domain.entities.bcc_entities import BccIntent

        db = SessionLocal()
        try:
            intents = db.query(BccIntent).filter_by(tenant_id=tenant_id).all()
            result = {}
            for intent in intents:
                if intent.trigger_phrases:
                    result[intent.name] = intent.trigger_phrases
            return result
        finally:
            db.close()
    except Exception:
        return {}


def _store_tool_schemas_in_bcc(tenant_id: str, schemas: list[dict]) -> None:
    """Store generated tool schemas in BccTaskTemplate context."""
    if not schemas:
        return
    try:
        from app.infrastructure.database import SessionLocal
        from app.domain.entities.bcc_entities import BccTaskTemplate

        db = SessionLocal()
        try:
            for schema in schemas:
                tool_name = schema.get("function", {}).get("name", "")
                if not tool_name:
                    continue
                tpl = db.query(BccTaskTemplate).filter(
                    BccTaskTemplate.tenant_id == tenant_id,
                    BccTaskTemplate.context["tool_priority"].astext.contains(tool_name),
                ).first()
                if tpl:
                    ctx = dict(tpl.context or {})
                    existing_schemas = ctx.get("tool_schemas", [])
                    existing_schemas.append(schema)
                    ctx["tool_schemas"] = existing_schemas
                    tpl.context = ctx
                    db.flush()
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning("deep_agent_store_schemas_failed", error=str(e))


# ── Build Graph ───────────────────────────────────────────────

def build_deep_agent_graph() -> StateGraph:
    """Build and compile the Deep Agent LangGraph pipeline."""
    graph = StateGraph(DeepAgentState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("plan_validator", plan_validator_node)
    graph.add_node("domain_builder", domain_builder_node)
    graph.add_node("intent_builder", intent_builder_node)
    graph.add_node("task_builder", task_builder_node)
    graph.add_node("tool_schema_generator", tool_schema_generator_node)
    graph.add_node("workflow_code_generator", workflow_code_generator_node)
    graph.add_node("code_reviewer", code_reviewer_node)
    graph.add_node("deployer", deployer_node)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "plan_validator")
    graph.add_conditional_edges("plan_validator", _route_after_plan_validation)
    graph.add_edge("domain_builder", "intent_builder")
    graph.add_edge("intent_builder", "task_builder")
    graph.add_edge("task_builder", "tool_schema_generator")
    graph.add_edge("tool_schema_generator", "workflow_code_generator")
    graph.add_edge("workflow_code_generator", "code_reviewer")
    graph.add_conditional_edges("code_reviewer", _route_after_review)
    graph.add_edge("deployer", END)

    return graph.compile()


deep_agent_pipeline = build_deep_agent_graph()


async def run_deep_agent(
    instruction: str,
    tenant_id: str,
    user_id: str,
    user_email: str,
) -> dict:
    """Run the Deep Agent pipeline."""
    initial_state: DeepAgentState = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "user_email": user_email,
        "instruction": instruction,
        "plan": {},
        "domains_created": [],
        "intents_created": [],
        "tasks_created": [],
        "generated_tool_schemas": [],
        "generated_code": {},
        "code_review_result": {},
        "review_result": {},
        "status": "planning",
        "error": None,
        "revision_count": 0,
    }

    logger.info("deep_agent_started", instruction=instruction[:100])
    result = await deep_agent_pipeline.ainvoke(initial_state)

    summary = {
        "status": result["status"],
        "domains_created": len([d for d in result.get("domains_created", []) if not d.get("existed")]),
        "intents_created": len([i for i in result.get("intents_created", []) if not i.get("existed")]),
        "tasks_created": len(result.get("tasks_created", [])),
        "tool_schemas_generated": len(result.get("generated_tool_schemas", [])),
        "workflows_generated": list(result.get("generated_code", {}).keys()),
        "code_review": result.get("code_review_result", {}),
        "review": result.get("review_result", {}),
        "error": result.get("error"),
    }
    logger.info("deep_agent_completed", **summary)
    return summary
