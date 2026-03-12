"""Workflow Engine for Bob — Layer 2 of the Intent Router.

Deterministic Python workflows that execute CRM actions based on
classified intents. No LLM decides the workflow — code does.

Supports pause/resume for multi-turn conversations (e.g. user picks
an organization from search results).
"""

import json
import uuid
import structlog
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)


# ── Workflow result types ─────────────────────────────────────

@dataclass
class WorkflowResult:
    """Result of a workflow execution step."""
    message: str
    actions: list[dict] = field(default_factory=list)
    tool_steps: list[dict] = field(default_factory=list)
    paused: bool = False
    resume_key: Optional[str] = None
    state: dict = field(default_factory=dict)
    artifact: Optional[dict] = None


@dataclass
class WorkflowContext:
    """Context passed to workflow functions."""
    db: Session
    tenant_id: str
    user_id: str
    user_email: str
    entities: Any  # ExtractedEntities from classifier
    user_message: str
    state: dict = field(default_factory=dict)
    session_messages: list[dict] = field(default_factory=list)  # full chat history for LLM extraction

    # Internal accumulators
    _actions: list[dict] = field(default_factory=list, repr=False)
    _tool_steps: list[dict] = field(default_factory=list, repr=False)
    _artifact: Optional[dict] = field(default=None, repr=False)

    def emit_action(self, action_type: str, **kwargs) -> None:
        """Emit a UI action to be sent to the frontend."""
        action = {"type": action_type, **kwargs}
        self._actions.append(action)

    def add_tool_step(self, tool: str, status: str = "ok") -> None:
        """Record a tool execution step for the frontend badge display."""
        self._tool_steps.append({"tool": tool, "status": status})

    def emit_artifact(
        self,
        artifact_type: str,
        title: str,
        fields: Optional[list[dict]] = None,
        status: str = "complete",
        columns: Optional[list[str]] = None,
        rows: Optional[list[list[str]]] = None,
        items: Optional[list[dict]] = None,
        sections: Optional[list[dict]] = None,
    ) -> None:
        """Set the inline artifact card to display in the chat."""
        art: dict = {
            "type": artifact_type,
            "title": title,
            "fields": fields or [],
            "status": status,
        }
        if columns is not None:
            art["columns"] = columns
        if rows is not None:
            art["rows"] = rows
        if items is not None:
            art["items"] = items
        if sections is not None:
            art["sections"] = sections
        self._artifact = art

    def pause(self, message: str, resume_key: str) -> WorkflowResult:
        """Pause the workflow and wait for user input."""
        return WorkflowResult(
            message=message,
            actions=list(self._actions),
            tool_steps=list(self._tool_steps),
            paused=True,
            resume_key=resume_key,
            state=dict(self.state),
            artifact=self._artifact,
        )

    def complete(self, message: str) -> WorkflowResult:
        """Complete the workflow with a final message."""
        return WorkflowResult(
            message=message,
            actions=list(self._actions),
            tool_steps=list(self._tool_steps),
            paused=False,
            state=dict(self.state),
            artifact=self._artifact,
        )


# ── Workflow registry ─────────────────────────────────────────

_WORKFLOWS: dict[str, Callable] = {}
_RESUME_HANDLERS: dict[str, Callable] = {}


def workflow(intent: str):
    """Decorator to register a workflow for an intent."""
    def decorator(fn):
        _WORKFLOWS[intent] = fn
        return fn
    return decorator


def resume_handler(resume_key: str):
    """Decorator to register a resume handler for a paused workflow."""
    def decorator(fn):
        _RESUME_HANDLERS[resume_key] = fn
        return fn
    return decorator


def get_workflow(intent: str) -> Optional[Callable]:
    """Get the workflow function for an intent."""
    return _WORKFLOWS.get(intent)


def get_resume_handler(resume_key: str) -> Optional[Callable]:
    """Get the resume handler for a paused workflow."""
    return _RESUME_HANDLERS.get(resume_key)


def load_generated_workflows() -> list[str]:
    """Scan app/agents/generated/ for .py files and import them.

    Each file should contain @workflow() decorated functions that
    auto-register into _WORKFLOWS on import. Returns list of loaded
    module names.
    """
    import importlib
    import importlib.util
    import os

    generated_dir = os.path.join(os.path.dirname(__file__), "generated")
    if not os.path.isdir(generated_dir):
        return []

    loaded = []
    for filename in sorted(os.listdir(generated_dir)):
        if not filename.endswith(".py") or filename == "__init__.py":
            continue

        module_name = f"app.agents.generated.{filename[:-3]}"
        filepath = os.path.join(generated_dir, filename)

        try:
            if module_name in importlib.sys.modules:
                importlib.reload(importlib.sys.modules[module_name])
            else:
                spec = importlib.util.spec_from_file_location(module_name, filepath)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    importlib.sys.modules[module_name] = mod
                    spec.loader.exec_module(mod)

            loaded.append(filename[:-3])
            logger.info("generated_workflow_loaded", module=module_name)
        except Exception as e:
            logger.error("generated_workflow_load_failed", module=module_name, error=str(e))

    return loaded


# Load generated workflows on import
load_generated_workflows()


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: create_prospect (SMART WIZARD with LLM Entity Extraction)
#
#  Uses entity_extractor to read chat history and collect all
#  info the user already gave. Only asks for what's missing.
#
#  Flow: extract → Rolodex search → pick → ask missing → finalize
# ═══════════════════════════════════════════════════════════════

# Required + optional fields for create_prospect
_PROSPECT_REQUIRED_FIELDS = {
    "org_name": "Organization/company/business name",
}
_PROSPECT_OPTIONAL_FIELDS = {
    "contact_first": "Contact first name",
    "contact_last": "Contact last name",
    "contact_email": "Contact email address",
    "opp_name": "Opportunity/deal name",
    "amount": "Deal monetary value",
    "product_name": "Product or service name",
}


@workflow("create_prospect")
def create_prospect_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Smart Step 1 — Extract entities from chat history, then decide next action."""
    from app.agents.entity_extractor import run_extraction

    # Run LLM extraction on the full chat history
    collected, missing = run_extraction(
        chat_history=ctx.session_messages,
        required_fields=_PROSPECT_REQUIRED_FIELDS,
        optional_fields=_PROSPECT_OPTIONAL_FIELDS,
    )

    # Store everything we got from extraction into workflow state
    for key, value in collected.items():
        if value and key not in ctx.state:
            ctx.state[key] = value

    logger.info(
        "prospect_extraction",
        collected=list(collected.keys()),
        missing=missing,
    )

    # If we have org_name → go straight to Rolodex search
    org_name = ctx.state.get("org_name")
    if org_name:
        ctx.state["org_query"] = org_name
        return _search_rolodex_and_show(ctx, org_name)

    # Still need org_name — ask for it
    return ctx.pause(
        message="What's the name of the organization? I'll check Bob's Rolodex 📇",
        resume_key="prospect_ask_org_name",
    )


@resume_handler("prospect_ask_org_name")
def resume_prospect_ask_org_name(ctx: WorkflowContext) -> WorkflowResult:
    """Resume — User gave the org name. Extract from history + search Rolodex."""
    from app.agents.entity_extractor import run_extraction

    # Re-run extraction with the new message in context
    collected, _ = run_extraction(
        chat_history=ctx.session_messages,
        required_fields=_PROSPECT_REQUIRED_FIELDS,
        optional_fields=_PROSPECT_OPTIONAL_FIELDS,
        already_collected={k: v for k, v in ctx.state.items() if v},
    )
    for key, value in collected.items():
        if value and key not in ctx.state:
            ctx.state[key] = value

    # org_name could come from extraction or direct message
    org_query = ctx.state.get("org_name") or ctx.user_message.strip()
    if not org_query:
        return ctx.pause(
            message="I need a name to search. What's the organization called?",
            resume_key="prospect_ask_org_name",
        )
    ctx.state["org_query"] = org_query
    return _search_rolodex_and_show(ctx, org_query)


def _search_rolodex_and_show(ctx: WorkflowContext, query: str) -> WorkflowResult:
    """Search Serper Maps API and present results to user."""
    import httpx
    from app.config import settings

    SERPER_URL = "https://google.serper.dev/maps"

    ctx.emit_artifact(
        artifact_type="search_results",
        title="Bob's Rolodex Search",
        fields=[{"label": "Query", "value": query}],
        status="building",
    )

    try:
        # Synchronous call (workflow engine is sync)
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                SERPER_URL,
                json={"q": query, "num": 8},
                headers={
                    "X-API-KEY": settings.serper_api_key,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()

        places = data.get("places", [])
        ctx.add_tool_step("search rolodex")

        if not places:
            logger.info("rolodex_search_empty", query=query)
            ctx.emit_artifact(
                artifact_type="search_results",
                title="Bob's Rolodex",
                fields=[{"label": "Query", "value": query}, {"label": "Results", "value": "0"}],
                status="complete",
            )
            ctx.state["org_name"] = query
            return ctx.pause(
                message=(
                    f"No results in Bob's Rolodex for **{query}**.\n\n"
                    f"I'll create a new organization called **{query}**.\n"
                    f"Who is the primary contact? (Name, email if you have it)"
                ),
                resume_key="prospect_ask_contact",
            )

        # Store results for selection
        rolodex_results = []
        for place in places:
            rolodex_results.append({
                "title": place.get("title", "Unknown"),
                "address": place.get("address", "N/A"),
                "phone": place.get("phoneNumber", ""),
                "website": place.get("website", ""),
                "industry": place.get("type", ""),
                "rating": place.get("rating"),
            })
        ctx.state["rolodex_results"] = rolodex_results

        # Build artifact with results — include ALL Maps data per result
        result_fields = [{"label": "Query", "value": query}]
        for i, r in enumerate(rolodex_results, 1):
            # Build a rich description with all Maps data
            parts = [r["title"]]
            if r.get("industry"):
                parts[0] += f" ({r['industry']})"
            parts.append(f"📍 {r['address']}")
            if r.get("phone"):
                parts.append(f"📞 {r['phone']}")
            if r.get("website"):
                parts.append(f"🌐 {r['website']}")
            if r.get("rating"):
                parts.append(f"⭐ {r['rating']}/5")

            result_fields.append({"label": f"#{i}", "value": " — ".join(parts)})

        ctx.emit_artifact(
            artifact_type="search_results",
            title="Bob's Rolodex",
            fields=result_fields,
            status="complete",
        )

        # Build text list
        lines = [f"📇 **Bob's Rolodex** found **{len(rolodex_results)}** result(s) for **{query}**:\n"]
        for i, r in enumerate(rolodex_results, 1):
            line = f"**{i}.** {r['title']}"
            if r.get("industry"):
                line += f" ({r['industry']})"
            line += f"\n   📍 {r['address']}"
            if r.get("phone"):
                line += f"\n   📞 {r['phone']}"
            if r.get("website"):
                line += f"\n   🌐 {r['website']}"
            lines.append(line)

        lines.append(f"\nWhich one? (Enter a number, or type a name to create a new one)")

        logger.info("rolodex_search_done", query=query, results=len(rolodex_results))

        return ctx.pause(
            message="\n".join(lines),
            resume_key="prospect_rolodex_pick",
        )

    except Exception as e:
        logger.error("rolodex_search_error", query=query, error=str(e))
        ctx.state["org_name"] = query
        return ctx.pause(
            message=(
                f"Bob's Rolodex is temporarily unavailable.\n"
                f"I'll create **{query}** as a new organization.\n"
                f"Who is the primary contact? (Name, email if you have it)"
            ),
            resume_key="prospect_ask_contact",
        )


@resume_handler("prospect_rolodex_pick")
def resume_prospect_rolodex_pick(ctx: WorkflowContext) -> WorkflowResult:
    """Step 3 — User picked a Rolodex result or typed a new name."""
    import re

    user_msg = ctx.user_message.strip()
    rolodex_results = ctx.state.get("rolodex_results", [])

    # Check if user typed a number
    num_match = re.search(r"^#?(\d+)$", user_msg)
    if num_match and rolodex_results:
        idx = int(num_match.group(1)) - 1
        if 0 <= idx < len(rolodex_results):
            selected = rolodex_results[idx]
            ctx.state["org_name"] = selected["title"]
            ctx.state["org_address"] = selected.get("address", "")
            ctx.state["org_phone"] = selected.get("phone", "")
            ctx.state["org_website"] = selected.get("website", "")
            ctx.state["org_industry"] = selected.get("industry", "")

            ctx.add_tool_step("select result")
            ctx.emit_artifact(
                artifact_type="organization",
                title=selected["title"],
                fields=[
                    {"label": "Name", "value": selected["title"]},
                    {"label": "Address", "value": selected.get("address", "—")},
                    {"label": "Industry", "value": selected.get("industry", "—")},
                ],
                status="building",
            )
            return ctx.pause(
                message=(
                    f"✅ Got it! Creating **{selected['title']}** from Bob's Rolodex.\n\n"
                    f"Who is the primary contact for this account? (Name, email if you have it)\n"
                    f"Or type **skip** to continue without a contact."
                ),
                resume_key="prospect_ask_contact",
            )

    # User typed a new name or re-search
    if user_msg.lower() in ["new", "nouveau", "nouvelle", "créer"]:
        return ctx.pause(
            message="What name for the new organization?",
            resume_key="prospect_manual_org_name",
        )

    # Treat as new org name directly
    ctx.state["org_name"] = user_msg
    return ctx.pause(
        message=(
            f"Got it! I'll create **{user_msg}** as a new organization.\n\n"
            f"Who is the primary contact? (Name, email if you have it)\n"
            f"Or type **skip** to continue without a contact."
        ),
        resume_key="prospect_ask_contact",
    )


@resume_handler("prospect_manual_org_name")
def resume_prospect_manual_org_name(ctx: WorkflowContext) -> WorkflowResult:
    """User wants a manually-named org."""
    org_name = ctx.user_message.strip()
    if not org_name:
        return ctx.pause(
            message="I need a name. What's the organization called?",
            resume_key="prospect_manual_org_name",
        )
    ctx.state["org_name"] = org_name
    return ctx.pause(
        message=(
            f"Creating **{org_name}**.\n\n"
            f"Who is the primary contact? (Name, email if you have it)\n"
            f"Or type **skip** to continue without a contact."
        ),
        resume_key="prospect_ask_contact",
    )


@resume_handler("prospect_ask_contact")
def resume_prospect_ask_contact(ctx: WorkflowContext) -> WorkflowResult:
    """Resume — Got contact info. Extract from history + ask for opp name."""
    from app.agents.entity_extractor import run_extraction
    user_msg = ctx.user_message.strip()

    if user_msg.lower() not in ["skip", "passer", "non", "no", "-", ""]:
        # Re-run extraction to pick up contact from chat history
        collected, _ = run_extraction(
            chat_history=ctx.session_messages,
            required_fields={"contact_first": "Contact first name", "contact_last": "Contact last name"},
            optional_fields={"contact_email": "Contact email", "opp_name": "Opportunity name"},
            already_collected={k: v for k, v in ctx.state.items() if v},
        )
        for key, value in collected.items():
            if value and key not in ctx.state:
                ctx.state[key] = value

        # Fallback: parse contact manually if extraction missed it
        if not ctx.state.get("contact_first"):
            import re
            email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', user_msg)
            if email_match:
                ctx.state["contact_email"] = email_match.group(0)
                name_part = user_msg.replace(email_match.group(0), "").strip().strip(",").strip()
            else:
                name_part = user_msg
            parts = name_part.split(None, 1)
            ctx.state["contact_first"] = parts[0] if parts else ""
            ctx.state["contact_last"] = parts[1] if len(parts) > 1 else ""

    # If we already have opp_name from extraction, skip asking
    if ctx.state.get("opp_name"):
        return _finalize_prospect(ctx)

    org_name = ctx.state.get("org_name", "")
    return ctx.pause(
        message=f"What should we call this opportunity? (or I'll use **{org_name}** by default)",
        resume_key="prospect_ask_opp_name",
    )


@resume_handler("prospect_ask_opp_name")
def resume_prospect_ask_opp_name(ctx: WorkflowContext) -> WorkflowResult:
    """Step 5 — Create everything and offer enrichment."""
    user_msg = ctx.user_message.strip()
    org_name = ctx.state.get("org_name", "New Organization")

    # Use user's answer or default to org name
    if user_msg.lower() in ["", "default", "oui", "yes", "ok"]:
        opp_name = org_name
    else:
        opp_name = user_msg

    ctx.state["opp_name"] = opp_name

    return _finalize_prospect(ctx)


def _finalize_prospect(ctx: WorkflowContext) -> WorkflowResult:
    """Create org, contact, opportunity and offer enrichment."""
    from app.domain.entities.organization import Organization
    from app.domain.entities.contact import Contact
    from app.domain.entities.opportunity import Opportunity

    org_name = ctx.state.get("org_name", "New Organization")
    opp_name = ctx.state.get("opp_name", org_name)

    # ── Create organization ────────────────────────
    org = Organization(
        name=org_name,
        address=ctx.state.get("org_address", ""),
        phone=ctx.state.get("org_phone", ""),
        website=ctx.state.get("org_website", ""),
        industry=ctx.state.get("org_industry", ""),
        tenant_id=ctx.tenant_id,
        created_by=ctx.user_email,
    )
    ctx.db.add(org)
    ctx.db.commit()
    ctx.db.refresh(org)
    ctx.add_tool_step("Create Organization")
    logger.info("workflow_org_created", org_id=str(org.id), name=org_name)

    # ── Create contact (if provided) ───────────────
    contact_id = None
    contact_first = ctx.state.get("contact_first", "")
    contact_last = ctx.state.get("contact_last", "")
    contact_email = ctx.state.get("contact_email", "")

    if contact_first or contact_last or contact_email:
        contact = Contact(
            first_name=contact_first,
            last_name=contact_last,
            email=contact_email,
            organization_id=org.id,
            tenant_id=ctx.tenant_id,
            created_by=ctx.user_email,
        )
        ctx.db.add(contact)
        ctx.db.commit()
        ctx.db.refresh(contact)
        contact_id = str(contact.id)
        ctx.add_tool_step("Create Contact")
        logger.info("workflow_contact_created", contact_id=contact_id)

    # ── Create opportunity ─────────────────────────
    opp = Opportunity(
        name=opp_name,
        organization_id=org.id,
        contact_id=contact_id,
        stage="PROSPECTING",
        source="Bob",
        tenant_id=ctx.tenant_id,
        created_by=ctx.user_email,
    )
    ctx.db.add(opp)
    ctx.db.commit()
    ctx.db.refresh(opp)
    ctx.add_tool_step("Create Opportunity")
    logger.info("workflow_opp_created", opp_id=str(opp.id))

    # ── Build final artifact ───────────────────────
    artifact_fields = [
        {"label": "Name", "value": opp_name},
        {"label": "Organization", "value": org_name},
        {"label": "Stage", "value": "PROSPECTING"},
        {"label": "Source", "value": "Bob"},
    ]
    if contact_first or contact_last:
        artifact_fields.append({"label": "Contact", "value": f"{contact_first} {contact_last}".strip()})

    ctx.emit_artifact(
        artifact_type="opportunity",
        title=opp_name,
        fields=artifact_fields,
        status="complete",
    )

    # Store org_id for enrichment
    ctx.state["org_id"] = str(org.id)

    # ── Success message + Enrichment offer ─────────
    parts = []
    parts.append(f"✅ **Account created!**")
    parts.append(f"- Organization: [**{org_name}**](/organizations/{org.id})")
    if contact_first or contact_last:
        parts.append(f"- Contact: **{contact_first} {contact_last}**")
    parts.append(f"- Opportunity: [**{opp_name}**](/opportunities/{opp.id})")
    parts.append("")
    parts.append("✨ **Make my magic with my rolodex?**")
    parts.append("Say **yes** and I'll deep-enrich this account with Bob's Rolodex.")

    return ctx.pause(
        message="\n".join(parts),
        resume_key="prospect_enrich_offer",
    )


@resume_handler("prospect_enrich_offer")
def resume_prospect_enrich_offer(ctx: WorkflowContext) -> WorkflowResult:
    """Step 6 (optional) — User accepts or declines enrichment."""
    user_msg = ctx.user_message.strip().lower()
    org_id = ctx.state.get("org_id")

    affirmative = any(w in user_msg for w in [
        "oui", "yes", "ok", "go", "magic", "rolodex", "enrich", "enrichir",
        "yep", "sure", "let's go", "do it", "vas-y", "fais-le",
    ])

    if not affirmative or not org_id:
        return ctx.complete(
            message="No problem! Your account is ready. Let me know if you need anything else 👋"
        )

    # Launch enrichment
    from app.domain.entities.organization import Organization
    from app.application.use_cases.enrich_organization import EnrichOrganizationUseCase
    from app.domain.entities.user import User

    org = ctx.db.query(Organization).filter(Organization.id == org_id).first()
    user = ctx.db.query(User).filter(User.id == ctx.user_id).first()

    if not org or not user:
        return ctx.complete(message="Could not find the organization for enrichment.")

    ctx.emit_artifact(
        artifact_type="enrichment",
        title=f"Enriching {org.name}...",
        fields=[{"label": "Status", "value": "Running..."}],
        status="building",
    )

    try:
        use_case = EnrichOrganizationUseCase(ctx.db)
        result = use_case.execute(
            organization_id=str(org.id),
            tenant_id=ctx.tenant_id,
            user_email=ctx.user_email,
            user_id=str(user.id),
        )

        fields_updated = result.get("fields_updated", 0)
        contacts_created = result.get("contacts_created", 0)
        status = result.get("status", "done")

        enrich_fields = [
            {"label": "Status", "value": "✅ Complete" if status == "done" else f"⚠️ {status}"},
            {"label": "Fields Updated", "value": str(fields_updated)},
            {"label": "Contacts Found", "value": str(contacts_created)},
        ]

        ctx.emit_artifact(
            artifact_type="enrichment",
            title=f"✨ {org.name} — Enriched",
            fields=enrich_fields,
            status="complete",
        )
        ctx.add_tool_step("Enrich Account")

        return ctx.complete(
            message=(
                f"✨ **Enrichment complete for {org.name}!**\n"
                f"- **{fields_updated}** fields updated\n"
                f"- **{contacts_created}** contacts discovered\n\n"
                f"[View enriched account →](/organizations/{org.id})"
            )
        )

    except Exception as e:
        logger.error("workflow_enrichment_error", org_id=org_id, error=str(e))
        ctx.emit_artifact(
            artifact_type="enrichment",
            title=f"{org.name} — Enrichment",
            fields=[{"label": "Status", "value": f"Error: {str(e)[:100]}"}],
            status="partial",
        )
        return ctx.complete(
            message=f"⚠️ Enrichment encountered an issue: {str(e)[:200]}\n\nYour account is still created though!"
        )


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: search_entity
#  Triggered by: "cherche Bell Canada", "trouve le contact", etc.
# ═══════════════════════════════════════════════════════════════

@workflow("search_entity")
def search_entity_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Search for an entity and show results in a popup."""
    entity_type = ctx.entities.entity_type or "organization"
    query = ctx.entities.search_query or ctx.entities.org_name or ""

    if entity_type == "organization":
        from app.domain.entities.organization import Organization
        results = ctx.db.query(Organization).filter(
            Organization.tenant_id == ctx.tenant_id,
            Organization.name.ilike(f"%{query}%") if query else True,
        ).limit(5).all()

        result_list = [
            {"id": str(o.id), "name": o.name, "industry": o.industry}
            for o in results
        ]

        ctx.add_tool_step("search organizations")
        if results:
            ctx.emit_action("search_entity", entity="organization", page="organizations", name=query)
            ctx.emit_action("ui_update_input", text=query, submit=True)

    elif entity_type == "contact":
        from app.domain.entities.contact import Contact
        results = ctx.db.query(Contact).filter(
            Contact.tenant_id == ctx.tenant_id,
        ).limit(5).all()

        result_list = [
            {"id": str(c.id), "name": f"{c.first_name} {c.last_name}", "email": c.email}
            for c in results
            if not query or query.lower() in f"{c.first_name} {c.last_name} {c.email or ''}".lower()
        ]

        ctx.add_tool_step("search contacts")
        if results:
            ctx.emit_action("search_entity", entity="contact", page="contacts", name=query)
    else:
        result_list = []

    if result_list:
        return ctx.complete(
            message=f"{len(result_list)} résultat(s) trouvé(s) pour « {query} »."
        )
    else:
        return ctx.complete(message=f"Aucun résultat trouvé pour « {query} ».")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: navigate
# ═══════════════════════════════════════════════════════════════

@workflow("navigate")
def navigate_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Navigate to a CRM page."""
    page = ctx.entities.page or "dashboard"
    page_map = {
        "dashboard": "dashboard",
        "organizations": "organizations",
        "contacts": "contacts",
        "opportunities": "opportunities",
        "quotes": "quotes",
        "activities": "activities",
        "settings": "settings",
        "training": "template/crm-mastery",
    }
    target = page_map.get(page.lower(), page)
    ctx.emit_action("navigate", page=target)
    return ctx.complete(message=f"Navigation vers {target}.")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: get_pipeline
# ═══════════════════════════════════════════════════════════════

@workflow("get_pipeline")
def get_pipeline_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Get pipeline stats."""
    from app.domain.entities.opportunity import Opportunity
    from sqlalchemy import func

    stats = ctx.db.query(
        Opportunity.stage,
        func.count(Opportunity.id),
        func.sum(Opportunity.amount),
    ).filter(
        Opportunity.tenant_id == ctx.tenant_id,
    ).group_by(Opportunity.stage).all()

    if not stats:
        return ctx.complete(message="Le pipeline est vide pour le moment.")

    lines = ["📊 **Pipeline de ventes** :\n"]
    total_count = 0
    total_value = 0.0
    for stage, count, value in stats:
        val = float(value or 0)
        total_count += count
        total_value += val
        lines.append(f"- **{stage}** : {count} opp. — {val:,.0f}$")

    lines.append(f"\n**Total** : {total_count} opportunités — {total_value:,.0f}$")
    return ctx.complete(message="\n".join(lines))


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: create_contact (standalone)
# ═══════════════════════════════════════════════════════════════

@workflow("create_contact")
def create_contact_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Create a contact without an opportunity."""
    from app.domain.entities.contact import Contact
    from app.domain.entities.organization import Organization

    e = ctx.entities
    org_id = None

    # Try to link to existing org
    if e.org_name:
        org = ctx.db.query(Organization).filter(
            Organization.tenant_id == ctx.tenant_id,
            Organization.name.ilike(f"%{e.org_name}%"),
        ).first()
        if org:
            org_id = org.id

    contact = Contact(
        first_name=e.contact_first or "",
        last_name=e.contact_last or "",
        email=e.email or "",
        phone=e.phone or "",
        organization_id=org_id,
        tenant_id=ctx.tenant_id,
        created_by=ctx.user_email,
    )
    ctx.db.add(contact)
    ctx.db.commit()
    ctx.db.refresh(contact)
    ctx.add_tool_step("create contact")

    name = f"{e.contact_first or ''} {e.contact_last or ''}".strip()
    return ctx.complete(message=f"✅ Contact créé : **{name}**" + (f" ({e.email})" if e.email else ""))


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: top_opportunities
#  "Mes 5 meilleures opportunités", "best deals"
# ═══════════════════════════════════════════════════════════════

@workflow("top_opportunities")
def top_opportunities_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Show top 5 opportunities by amount."""
    from app.domain.entities.opportunity import Opportunity

    opps = ctx.db.query(Opportunity).filter(
        Opportunity.tenant_id == ctx.tenant_id,
        Opportunity.amount.isnot(None),
    ).order_by(Opportunity.amount.desc()).limit(5).all()

    if not opps:
        return ctx.complete(message="Aucune opportunité avec montant trouvée.")

    rows = []
    for opp in opps:
        rows.append([
            opp.name,
            opp.organization_name or "—",
            opp.stage or "—",
            f"{float(opp.amount or 0):,.0f}$",
        ])

    ctx.emit_artifact("data_table",
        title=f"Top {len(opps)} Opportunités",
        columns=["Nom", "Organisation", "Étape", "Montant"],
        rows=rows,
    )
    ctx.add_tool_step("list top opportunities")
    return ctx.complete(message=f"Voici vos **{len(opps)} meilleures opportunités** par montant :")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: closing_this_month
# ═══════════════════════════════════════════════════════════════

@workflow("closing_this_month")
def closing_this_month_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Opportunities expected to close this month."""
    from app.domain.entities.opportunity import Opportunity
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    month_end = now.replace(day=28) + timedelta(days=4)
    month_end = month_end.replace(day=1) - timedelta(days=1)

    opps = ctx.db.query(Opportunity).filter(
        Opportunity.tenant_id == ctx.tenant_id,
        Opportunity.close_date >= now.date(),
        Opportunity.close_date <= month_end.date(),
    ).order_by(Opportunity.close_date).limit(10).all()

    if not opps:
        return ctx.complete(message="Aucune opportunité à conclure ce mois-ci.")

    rows = []
    for opp in opps:
        rows.append([
            opp.name,
            opp.organization_name or "—",
            opp.stage or "—",
            str(opp.close_date) if opp.close_date else "—",
            f"{float(opp.amount or 0):,.0f}$" if opp.amount else "—",
        ])

    ctx.emit_artifact("data_table",
        title=f"À closer — {now.strftime('%B %Y')}",
        columns=["Nom", "Organisation", "Étape", "Date", "Montant"],
        rows=rows,
    )
    ctx.add_tool_step("closing this month")
    return ctx.complete(message=f"**{len(opps)}** opportunité(s) à conclure ce mois-ci.")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: stale_deals
# ═══════════════════════════════════════════════════════════════

@workflow("stale_deals")
def stale_deals_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Deals unchanged for 30+ days."""
    from app.domain.entities.opportunity import Opportunity
    from datetime import datetime, timedelta

    threshold = datetime.utcnow() - timedelta(days=30)

    opps = ctx.db.query(Opportunity).filter(
        Opportunity.tenant_id == ctx.tenant_id,
        Opportunity.updated_at < threshold,
        Opportunity.stage.notin_(["CLOSED_WON", "CLOSED_LOST"]),
    ).order_by(Opportunity.updated_at).limit(10).all()

    if not opps:
        return ctx.complete(message="Aucun deal stagnant — bravo ! 🎉")

    rows = []
    for opp in opps:
        days_stale = (datetime.utcnow() - opp.updated_at).days if opp.updated_at else 0
        rows.append([
            opp.name,
            opp.organization_name or "—",
            opp.stage or "—",
            f"{days_stale}j",
            f"{float(opp.amount or 0):,.0f}$" if opp.amount else "—",
        ])

    ctx.emit_artifact("data_table",
        title="Deals stagnants (+30j)",
        columns=["Nom", "Organisation", "Étape", "Inactif", "Montant"],
        rows=rows,
    )
    ctx.add_tool_step("stale deals")
    return ctx.complete(message=f"⚠️ **{len(opps)}** deal(s) stagnant(s) depuis plus de 30 jours.")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: pipeline_value (enriched get_pipeline)
# ═══════════════════════════════════════════════════════════════

@workflow("pipeline_value")
def pipeline_value_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Pipeline value breakdown with visual stats."""
    from app.domain.entities.opportunity import Opportunity
    from sqlalchemy import func

    stats_q = ctx.db.query(
        Opportunity.stage,
        func.count(Opportunity.id),
        func.sum(Opportunity.amount),
    ).filter(
        Opportunity.tenant_id == ctx.tenant_id,
    ).group_by(Opportunity.stage).all()

    if not stats_q:
        return ctx.complete(message="Le pipeline est vide.")

    kpi_items = []
    total_value = 0.0
    total_count = 0
    for stage, count, value in stats_q:
        val = float(value or 0)
        total_count += count
        total_value += val
        kpi_items.append({"label": stage, "value": f"{val:,.0f}$"})

    kpi_items.insert(0, {"label": "Total Pipeline", "value": f"{total_value:,.0f}$", "change": f"{total_count} deals"})

    ctx.emit_artifact("kpi_summary",
        title="Valeur du Pipeline",
        items=kpi_items,
    )
    ctx.add_tool_step("pipeline value")
    return ctx.complete(message=f"📊 Pipeline : **{total_count}** deals — **{total_value:,.0f}$**")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: dormant_contacts
# ═══════════════════════════════════════════════════════════════

@workflow("dormant_contacts")
def dormant_contacts_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Contacts not contacted in 5+ months."""
    from app.domain.entities.contact import Contact
    from datetime import datetime, timedelta

    threshold = datetime.utcnow() - timedelta(days=150)  # ~5 months

    contacts = ctx.db.query(Contact).filter(
        Contact.tenant_id == ctx.tenant_id,
        Contact.updated_at < threshold,
    ).order_by(Contact.updated_at).limit(10).all()

    if not contacts:
        return ctx.complete(message="Tous vos contacts ont été contactés récemment ! ✅")

    rows = []
    for c in contacts:
        days = (datetime.utcnow() - c.updated_at).days if c.updated_at else 0
        name = f"{c.first_name or ''} {c.last_name or ''}".strip() or "Sans nom"
        rows.append([name, c.email or "—", f"{days}j"])

    ctx.emit_artifact("data_table",
        title="Contacts dormants (5+ mois)",
        columns=["Nom", "Email", "Inactif"],
        rows=rows,
    )
    ctx.add_tool_step("dormant contacts")
    return ctx.complete(message=f"📞 **{len(contacts)}** contact(s) à relancer — inactifs depuis plus de 5 mois.")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: recent_contacts
# ═══════════════════════════════════════════════════════════════

@workflow("recent_contacts")
def recent_contacts_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Recently added contacts."""
    from app.domain.entities.contact import Contact

    contacts = ctx.db.query(Contact).filter(
        Contact.tenant_id == ctx.tenant_id,
    ).order_by(Contact.created_at.desc()).limit(10).all()

    if not contacts:
        return ctx.complete(message="Aucun contact dans le CRM.")

    rows = []
    for c in contacts:
        name = f"{c.first_name or ''} {c.last_name or ''}".strip() or "Sans nom"
        rows.append([
            name,
            c.email or "—",
            c.phone or "—",
            str(c.created_at.date()) if c.created_at else "—",
        ])

    ctx.emit_artifact("data_table",
        title="Contacts récents",
        columns=["Nom", "Email", "Téléphone", "Ajouté le"],
        rows=rows,
    )
    ctx.add_tool_step("recent contacts")
    return ctx.complete(message=f"Voici les **{len(contacts)} derniers contacts** ajoutés :")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: contacts_no_email
# ═══════════════════════════════════════════════════════════════

@workflow("contacts_no_email")
def contacts_no_email_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Contacts missing email."""
    from app.domain.entities.contact import Contact
    from sqlalchemy import or_

    contacts = ctx.db.query(Contact).filter(
        Contact.tenant_id == ctx.tenant_id,
        or_(Contact.email == None, Contact.email == ""),  # noqa: E711
    ).limit(10).all()

    if not contacts:
        return ctx.complete(message="Tous vos contacts ont un email ! ✅")

    rows = []
    for c in contacts:
        name = f"{c.first_name or ''} {c.last_name or ''}".strip() or "Sans nom"
        rows.append([name, c.phone or "—"])

    ctx.emit_artifact("data_table",
        title="Contacts sans email",
        columns=["Nom", "Téléphone"],
        rows=rows,
    )
    ctx.add_tool_step("contacts no email")
    return ctx.complete(message=f"⚠️ **{len(contacts)}** contact(s) sans adresse email.")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: accounts_no_opp
# ═══════════════════════════════════════════════════════════════

@workflow("accounts_no_opp")
def accounts_no_opp_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Organizations with no opportunities."""
    from app.domain.entities.organization import Organization
    from app.domain.entities.opportunity import Opportunity
    from sqlalchemy import func

    # Subquery: org IDs that have at least one opp
    orgs_with_opp = ctx.db.query(Opportunity.organization_id).filter(
        Opportunity.tenant_id == ctx.tenant_id,
        Opportunity.organization_id.isnot(None),
    ).distinct().subquery()

    orgs = ctx.db.query(Organization).filter(
        Organization.tenant_id == ctx.tenant_id,
        ~Organization.id.in_(ctx.db.query(orgs_with_opp)),
    ).limit(10).all()

    if not orgs:
        return ctx.complete(message="Tous vos comptes ont au moins une opportunité ! ✅")

    rows = []
    for o in orgs:
        rows.append([o.name, o.industry or "—", o.status or "—"])

    ctx.emit_artifact("data_table",
        title="Comptes sans opportunité",
        columns=["Nom", "Industrie", "Statut"],
        rows=rows,
    )
    ctx.add_tool_step("accounts without opportunity")
    return ctx.complete(message=f"📋 **{len(orgs)}** compte(s) sans aucune opportunité — du potentiel inexploité !")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: most_active_accounts
# ═══════════════════════════════════════════════════════════════

@workflow("most_active_accounts")
def most_active_accounts_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Top accounts by opportunity count."""
    from app.domain.entities.organization import Organization
    from app.domain.entities.opportunity import Opportunity
    from sqlalchemy import func

    results = ctx.db.query(
        Organization.id,
        Organization.name,
        Organization.industry,
        func.count(Opportunity.id).label("opp_count"),
        func.sum(Opportunity.amount).label("total_amount"),
    ).join(Opportunity, Opportunity.organization_id == Organization.id).filter(
        Organization.tenant_id == ctx.tenant_id,
    ).group_by(Organization.id, Organization.name, Organization.industry
    ).order_by(func.count(Opportunity.id).desc()).limit(5).all()

    if not results:
        return ctx.complete(message="Aucun compte avec opportunité trouvé.")

    rows = []
    for row in results:
        rows.append([
            row.name,
            row.industry or "—",
            str(row.opp_count),
            f"{float(row.total_amount or 0):,.0f}$",
        ])

    ctx.emit_artifact("data_table",
        title="Comptes les plus actifs",
        columns=["Nom", "Industrie", "Opps", "Montant total"],
        rows=rows,
    )
    ctx.add_tool_step("most active accounts")
    return ctx.complete(message=f"🔥 Voici vos **{len(results)} comptes les plus actifs** :")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: accounts_by_industry
# ═══════════════════════════════════════════════════════════════

@workflow("accounts_by_industry")
def accounts_by_industry_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Account breakdown by industry."""
    from app.domain.entities.organization import Organization
    from sqlalchemy import func

    results = ctx.db.query(
        Organization.industry,
        func.count(Organization.id),
    ).filter(
        Organization.tenant_id == ctx.tenant_id,
        Organization.industry.isnot(None),
        Organization.industry != "",
    ).group_by(Organization.industry
    ).order_by(func.count(Organization.id).desc()).all()

    if not results:
        return ctx.complete(message="Aucune donnée d'industrie disponible.")

    total = sum(c for _, c in results)
    kpi_items = []
    for industry, count in results:
        pct = f"{count / total * 100:.0f}%" if total else "0%"
        kpi_items.append({"label": industry or "Non spécifié", "value": str(count), "change": pct})

    ctx.emit_artifact("pipeline",
        title=f"Comptes par industrie ({len(results)})",
        items=[{"label": industry or "Non spécifié", "value": str(count), "percent": round(count / total * 100) if total else 0} for industry, count in results],
    )
    ctx.add_tool_step("accounts by industry")
    return ctx.complete(message=f"📊 Répartition de vos comptes par industrie ({len(results)} industries) :")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: list_products
# ═══════════════════════════════════════════════════════════════

@workflow("list_products")
def list_products_flow(ctx: WorkflowContext) -> WorkflowResult:
    """List available products."""
    from app.domain.entities.product import Product

    products = ctx.db.query(Product).filter(
        Product.tenant_id == ctx.tenant_id,
    ).order_by(Product.name).limit(15).all()

    if not products:
        return ctx.complete(message="Aucun produit dans le catalogue.")

    rows = []
    for p in products:
        rows.append([
            p.name,
            p.category or "—",
            p.sku or "—",
            f"{float(p.price or 0):,.2f}$" if p.price else "—",
        ])

    ctx.emit_artifact("data_table",
        title=f"Catalogue Produits ({len(products)})",
        columns=["Nom", "Catégorie", "SKU", "Prix"],
        rows=rows,
    )
    ctx.add_tool_step("list products")
    return ctx.complete(message=f"Voici les **{len(products)} produits** du catalogue :")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: daily_summary
# ═══════════════════════════════════════════════════════════════

@workflow("daily_summary")
def daily_summary_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Full daily summary with stats."""
    from app.domain.entities.opportunity import Opportunity
    from app.domain.entities.contact import Contact
    from app.domain.entities.organization import Organization
    from sqlalchemy import func
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Total pipeline
    pipeline = ctx.db.query(
        func.count(Opportunity.id),
        func.sum(Opportunity.amount),
    ).filter(
        Opportunity.tenant_id == ctx.tenant_id,
        Opportunity.stage.notin_(["CLOSED_WON", "CLOSED_LOST"]),
    ).first()

    total_opps = pipeline[0] if pipeline else 0
    total_value = float(pipeline[1] or 0) if pipeline else 0

    # Stale count
    threshold_30 = now - timedelta(days=30)
    stale_count = ctx.db.query(func.count(Opportunity.id)).filter(
        Opportunity.tenant_id == ctx.tenant_id,
        Opportunity.updated_at < threshold_30,
        Opportunity.stage.notin_(["CLOSED_WON", "CLOSED_LOST"]),
    ).scalar() or 0

    # Contact count
    contact_count = ctx.db.query(func.count(Contact.id)).filter(
        Contact.tenant_id == ctx.tenant_id,
    ).scalar() or 0

    # Org count
    org_count = ctx.db.query(func.count(Organization.id)).filter(
        Organization.tenant_id == ctx.tenant_id,
    ).scalar() or 0

    kpi_items = [
        {"label": "Pipeline actif", "value": f"{total_value:,.0f}$"},
        {"label": "Deals ouverts", "value": str(total_opps)},
        {"label": "Deals stagnants", "value": str(stale_count), "change": "⚠️" if stale_count > 0 else "✅"},
        {"label": "Contacts", "value": str(contact_count)},
        {"label": "Organisations", "value": str(org_count)},
    ]

    ctx.emit_artifact("kpi_summary",
        title=f"Résumé — {now.strftime('%A %d %B %Y')}",
        items=kpi_items,
    )
    ctx.add_tool_step("daily summary")
    return ctx.complete(
        message=(
            f"☀️ **Bonjour !** Votre pipeline : **{total_value:,.0f}$** "
            f"({total_opps} deals ouverts"
            + (f", ⚠️ {stale_count} stagnants" if stale_count else "")
            + ")"
        )
    )


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: create_activity
#  "Note un appel avec Jean", "Crée un rappel pour demain"
# ═══════════════════════════════════════════════════════════════

@workflow("create_activity")
def create_activity_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Create a new activity (call, email, meeting, task, note)."""
    from app.domain.entities.activity import Activity, ActivityType, ActivityStatus, ActivityPriority
    from datetime import datetime

    e = ctx.entities

    # Determine activity type from context
    msg_lower = ctx.user_message.lower()
    if any(w in msg_lower for w in ["appel", "call", "téléphone", "phone"]):
        activity_type = ActivityType.CALL
    elif any(w in msg_lower for w in ["email", "courriel", "mail"]):
        activity_type = ActivityType.EMAIL
    elif any(w in msg_lower for w in ["réunion", "meeting", "rencontre"]):
        activity_type = ActivityType.MEETING
    elif any(w in msg_lower for w in ["note", "remarque"]):
        activity_type = ActivityType.NOTE
    else:
        activity_type = ActivityType.TASK

    # Build subject from entities or message
    contact_name = ""
    if e.contact_first or e.contact_last:
        contact_name = f"{e.contact_first or ''} {e.contact_last or ''}".strip()

    subject = f"{activity_type.value}: {contact_name}" if contact_name else f"{activity_type.value}: {ctx.user_message[:80]}"

    # Try to find contact by name if provided
    contact_id = None
    if contact_name:
        from app.domain.entities.contact import Contact
        contact = ctx.db.query(Contact).filter(
            Contact.tenant_id == ctx.tenant_id,
            Contact.first_name.ilike(f"%{e.contact_first or ''}%"),
        ).first()
        if contact:
            contact_id = contact.id

    activity = Activity(
        subject=subject,
        description=ctx.user_message,
        activity_type=activity_type,
        priority=ActivityPriority.MEDIUM,
        status=ActivityStatus.COMPLETED if activity_type == ActivityType.CALL else ActivityStatus.PENDING,
        due_date=datetime.utcnow() if activity_type in (ActivityType.CALL, ActivityType.NOTE) else None,
        completed_at=datetime.utcnow() if activity_type == ActivityType.CALL else None,
        contact_id=contact_id,
        tenant_id=ctx.tenant_id,
        owner_id=ctx.user_id,
        created_by=ctx.user_email,
    )
    ctx.db.add(activity)
    ctx.db.commit()
    ctx.db.refresh(activity)
    ctx.add_tool_step("create activity")

    type_labels = {
        "CALL": "📞 Appel",
        "EMAIL": "📧 Email",
        "MEETING": "🤝 Réunion",
        "TASK": "📋 Tâche",
        "NOTE": "📝 Note",
    }
    label = type_labels.get(activity_type.value, activity_type.value)

    return ctx.complete(
        message=f"✅ {label} créé : **{subject}**"
        + (f" — lié au contact **{contact_name}**" if contact_name and contact_id else "")
    )


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: today_activities
#  "Mes activités du jour", "Quoi de prévu aujourd'hui"
# ═══════════════════════════════════════════════════════════════

@workflow("today_activities")
def today_activities_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Activities due today."""
    from app.domain.entities.activity import Activity, ActivityStatus
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    activities = ctx.db.query(Activity).filter(
        Activity.tenant_id == ctx.tenant_id,
        Activity.due_date >= today_start,
        Activity.due_date < today_end,
    ).order_by(Activity.due_date).limit(15).all()

    if not activities:
        return ctx.complete(message="📭 Aucune activité prévue pour aujourd'hui.")

    rows = []
    for a in activities:
        atype = a.activity_type.value if hasattr(a.activity_type, 'value') else str(a.activity_type)
        status = a.status.value if hasattr(a.status, 'value') else str(a.status)
        rows.append([
            a.subject,
            atype,
            status,
            a.description[:60] + "..." if a.description and len(a.description) > 60 else (a.description or "—"),
        ])

    completed = sum(1 for a in activities if (a.status.value if hasattr(a.status, 'value') else str(a.status)) == "COMPLETED")
    pending = len(activities) - completed

    ctx.emit_artifact("data_table",
        title=f"Activités du jour — {now.strftime('%A %d %B')}",
        columns=["Sujet", "Type", "Statut", "Description"],
        rows=rows,
    )
    ctx.add_tool_step("today activities")
    return ctx.complete(message=f"📅 **{len(activities)}** activité(s) aujourd'hui — {completed} complétées, {pending} restantes.")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: overdue_activities
#  "Des rappels en retard ?", "Activités manquées"
# ═══════════════════════════════════════════════════════════════

@workflow("overdue_activities")
def overdue_activities_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Overdue activities (past due, not completed)."""
    from app.domain.entities.activity import Activity, ActivityStatus
    from datetime import datetime

    now = datetime.utcnow()

    activities = ctx.db.query(Activity).filter(
        Activity.tenant_id == ctx.tenant_id,
        Activity.due_date < now,
        Activity.status.in_([ActivityStatus.PENDING, ActivityStatus.IN_PROGRESS]),
    ).order_by(Activity.due_date).limit(10).all()

    if not activities:
        return ctx.complete(message="✅ Aucun rappel en retard — tout est à jour !")

    rows = []
    for a in activities:
        days_overdue = (now - a.due_date).days if a.due_date else 0
        atype = a.activity_type.value if hasattr(a.activity_type, 'value') else str(a.activity_type)
        rows.append([
            a.subject,
            atype,
            str(a.due_date.date()) if a.due_date else "—",
            f"{days_overdue}j",
        ])

    ctx.emit_artifact("data_table",
        title=f"Rappels en retard ({len(activities)})",
        columns=["Sujet", "Type", "Échéance", "Retard"],
        rows=rows,
    )
    ctx.add_tool_step("overdue activities")
    return ctx.complete(message=f"⚠️ **{len(activities)}** activité(s) en retard — à traiter rapidement !")


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: build_bcc
#  Triggered by: "Configure Bob", "Set up BCC", "Build the cognitive structure"
# ═══════════════════════════════════════════════════════════════

@workflow("build_bcc")
def build_bcc_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Deep Agent invocation — plan, confirm, then build BCC structure.

    Step 1 (initial): Show the plan from supervisor, pause for confirmation.
    Step 2 (resume): Run the full deep agent graph.
    """
    import asyncio
    from app.agents.deep_agent_graph import supervisor_node, DeepAgentState

    instruction = ctx.user_message or ctx.entities.search_query or "Build the default BCC cognitive structure"

    agent_state: DeepAgentState = {
        "tenant_id": ctx.tenant_id,
        "user_id": ctx.user_id,
        "user_email": ctx.user_email,
        "instruction": instruction,
        "plan": {},
        "domains_created": [],
        "intents_created": [],
        "tasks_created": [],
        "review_result": {},
        "status": "planning",
        "error": None,
        "revision_count": 0,
    }

    agent_state = supervisor_node(agent_state)
    if agent_state.get("error"):
        return ctx.complete(message=f"Deep Agent failed to plan: {agent_state['error']}")

    plan = agent_state.get("plan", {})
    domains = plan.get("domains", [])
    total_intents = sum(len(d.get("intents", [])) for d in domains)
    total_tasks = sum(
        len(t.get("tasks", []))
        for d in domains
        for t in d.get("intents", [])
    )

    plan_summary = f"🧠 **Deep Agent Plan**\n\n"
    plan_summary += f"I'll create **{len(domains)} domains**, **{total_intents} intents**, and **{total_tasks} tasks**.\n\n"
    for d in domains:
        plan_summary += f"**{d['name']}** ({d.get('icon', '')})\n"
        for i in d.get("intents", []):
            plan_summary += f"  • `{i['name']}` — {len(i.get('tasks', []))} tasks"
            if i.get("workflow_key"):
                plan_summary += f" (workflow: `{i['workflow_key']}`)"
            plan_summary += "\n"
        plan_summary += "\n"
    plan_summary += "**Confirm to proceed.** Say 'yes' or 'confirm'."

    ctx.state["deep_agent_plan"] = plan
    ctx.state["deep_agent_instruction"] = instruction
    ctx.add_tool_step("deep_agent_supervisor")

    return ctx.pause(message=plan_summary, resume_key="build_bcc_confirm")


@resume_handler("build_bcc_confirm")
def build_bcc_confirm(ctx: WorkflowContext) -> WorkflowResult:
    """Execute the Deep Agent after user confirmation."""
    import asyncio
    from app.agents.deep_agent_graph import run_deep_agent

    user_msg = (ctx.user_message or "").lower().strip()
    if user_msg not in ("yes", "oui", "confirm", "confirme", "go", "ok", "y"):
        return ctx.complete(message="Deep Agent execution cancelled.")

    plan = ctx.state.get("deep_agent_plan", {})
    instruction = ctx.state.get("deep_agent_instruction", "")

    ctx.add_tool_step("deep_agent_building")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    asyncio.run,
                    run_deep_agent(
                        instruction=instruction,
                        tenant_id=ctx.tenant_id,
                        user_id=ctx.user_id,
                        user_email=ctx.user_email,
                    ),
                ).result()
        else:
            result = asyncio.run(run_deep_agent(
                instruction=instruction,
                tenant_id=ctx.tenant_id,
                user_id=ctx.user_id,
                user_email=ctx.user_email,
            ))
    except Exception as e:
        return ctx.complete(message=f"Deep Agent failed: {str(e)}")

    if result.get("error"):
        return ctx.complete(message=f"Deep Agent encountered an error: {result['error']}")

    msg = (
        f"✅ **Deep Agent completed!**\n\n"
        f"- **{result.get('domains_created', 0)}** new domains\n"
        f"- **{result.get('intents_created', 0)}** new intents\n"
        f"- **{result.get('tasks_created', 0)}** new tasks\n\n"
    )

    review = result.get("review", {})
    if review.get("summary"):
        msg += f"**Review:** {review['summary']}\n\n"

    msg += "View your updated cognitive structure in **BCC → Cognitive Flow**."

    ctx.add_tool_step("deep_agent_complete")
    return ctx.complete(message=msg)

