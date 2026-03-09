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

    # Internal accumulators
    _actions: list[dict] = field(default_factory=list, repr=False)
    _tool_steps: list[dict] = field(default_factory=list, repr=False)

    def emit_action(self, action_type: str, **kwargs) -> None:
        """Emit a UI action to be sent to the frontend."""
        action = {"type": action_type, **kwargs}
        self._actions.append(action)

    def add_tool_step(self, tool: str, status: str = "ok") -> None:
        """Record a tool execution step for the frontend badge display."""
        self._tool_steps.append({"tool": tool, "status": status})

    def pause(self, message: str, resume_key: str) -> WorkflowResult:
        """Pause the workflow and wait for user input."""
        return WorkflowResult(
            message=message,
            actions=list(self._actions),
            tool_steps=list(self._tool_steps),
            paused=True,
            resume_key=resume_key,
            state=dict(self.state),
        )

    def complete(self, message: str) -> WorkflowResult:
        """Complete the workflow with a final message."""
        return WorkflowResult(
            message=message,
            actions=list(self._actions),
            tool_steps=list(self._tool_steps),
            paused=False,
            state=dict(self.state),
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


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: create_prospect
#  Triggered by: "nouveau prospect", "ajoute une opportunité", etc.
# ═══════════════════════════════════════════════════════════════

@workflow("create_prospect")
def create_prospect_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Full prospect creation flow: search org → popup → contact → opportunity."""
    from app.domain.entities.organization import Organization

    org_name = ctx.entities.org_name or ""

    # Step 1 — ALWAYS search for existing org
    if org_name:
        orgs = ctx.db.query(Organization).filter(
            Organization.tenant_id == ctx.tenant_id,
            Organization.name.ilike(f"%{org_name}%"),
        ).limit(5).all()
    else:
        orgs = []

    if orgs:
        # Existing org(s) found — show popup and ask user to pick
        org_list = [
            {"id": str(o.id), "name": o.name, "industry": o.industry, "phone": o.phone}
            for o in orgs
        ]

        ctx.add_tool_step("search organizations")
        ctx.emit_action("search_entity", entity="organization", page="organizations", name=org_name)
        ctx.emit_action("ui_update_input", text=org_name, submit=True)

        # Build numbered list for the message
        org_lines = []
        for i, o in enumerate(org_list, 1):
            line = f"#{i} — {o['name']}"
            if o.get("industry"):
                line += f" ({o['industry']})"
            org_lines.append(line)

        ctx.state["org_results"] = org_list
        ctx.state["original_entities"] = {
            "contact_first": ctx.entities.contact_first,
            "contact_last": ctx.entities.contact_last,
            "email": ctx.entities.email,
            "phone": ctx.entities.phone,
            "product_name": ctx.entities.product_name,
            "quantity": ctx.entities.quantity,
            "amount": ctx.entities.amount,
        }

        return ctx.pause(
            message=(
                f"J'ai trouvé {len(orgs)} organisation(s) correspondant à « {org_name} ». "
                f"Veuillez choisir par numéro :\n\n"
                + "\n".join(org_lines)
                + "\n\nOu tapez « nouveau » pour créer une nouvelle organisation."
            ),
            resume_key="prospect_org_selected",
        )
    else:
        # No existing org — create new one
        return _create_prospect_with_new_org(ctx, org_name)


def _create_prospect_with_new_org(ctx: WorkflowContext, org_name: str) -> WorkflowResult:
    """Create prospect with a brand new organization."""
    from app.domain.entities.organization import Organization

    if org_name:
        org = Organization(
            name=org_name,
            tenant_id=ctx.tenant_id,
            created_by=ctx.user_email,
        )
        ctx.db.add(org)
        ctx.db.commit()
        ctx.db.refresh(org)
        ctx.add_tool_step("create organization")
        ctx.state["org_id"] = str(org.id)
        ctx.state["org_name"] = org.name
        logger.info("workflow_org_created", org_id=str(org.id), name=org_name)
    else:
        ctx.state["org_id"] = None
        ctx.state["org_name"] = ""

    return _create_contact_and_opportunity(ctx)


def _create_contact_and_opportunity(ctx: WorkflowContext) -> WorkflowResult:
    """Create contact + opportunity using accumulated state."""
    from app.domain.entities.contact import Contact
    from app.domain.entities.opportunity import Opportunity

    org_id = ctx.state.get("org_id")
    org_name = ctx.state.get("org_name", "")
    entities = ctx.entities

    # Resolve entity data (from original or resumed state)
    contact_first = entities.contact_first or ctx.state.get("contact_first", "")
    contact_last = entities.contact_last or ctx.state.get("contact_last", "")
    email = entities.email or ctx.state.get("email", "")
    phone = entities.phone or ctx.state.get("phone", "")
    product_name = entities.product_name or ctx.state.get("product_name", "")
    quantity = entities.quantity or ctx.state.get("quantity")
    amount = entities.amount or ctx.state.get("amount")

    # Create contact if we have at least a name
    contact_id = None
    if contact_first or contact_last or email:
        contact = Contact(
            first_name=contact_first or "",
            last_name=contact_last or "",
            email=email or "",
            phone=phone or "",
            organization_id=org_id,
            tenant_id=ctx.tenant_id,
            created_by=ctx.user_email,
        )
        ctx.db.add(contact)
        ctx.db.commit()
        ctx.db.refresh(contact)
        contact_id = str(contact.id)
        ctx.add_tool_step("create contact")
        logger.info("workflow_contact_created", contact_id=contact_id)

    # Build opportunity name
    opp_name = product_name or "Nouvelle opportunité"
    if quantity:
        opp_name += f" - {quantity} users"

    opp = Opportunity(
        name=opp_name,
        organization_id=org_id,
        contact_id=contact_id,
        stage="PROSPECTING",
        source="Bob",
        amount=amount,
        tenant_id=ctx.tenant_id,
        created_by=ctx.user_email,
    )
    ctx.db.add(opp)
    ctx.db.commit()
    ctx.db.refresh(opp)
    ctx.add_tool_step("create opportunity")
    logger.info("workflow_opp_created", opp_id=str(opp.id))

    # Build success message
    parts = [f"✅ Opportunité créée : **{opp_name}**"]
    if org_name:
        parts.append(f"Organisation : **{org_name}**")
    if contact_first or contact_last:
        parts.append(f"Contact : **{contact_first} {contact_last}**" + (f" ({email})" if email else ""))
    if amount:
        parts.append(f"Valeur : **{amount:,.0f}$**")

    return ctx.complete(message="\n".join(parts))


@resume_handler("prospect_org_selected")
def resume_prospect_org_selected(ctx: WorkflowContext) -> WorkflowResult:
    """Resume after user selects an org from the search popup."""
    user_msg = ctx.user_message.strip().lower()
    org_results = ctx.state.get("org_results", [])
    original_entities = ctx.state.get("original_entities", {})

    # Restore original entities into state for downstream steps
    for key, val in original_entities.items():
        if val is not None:
            ctx.state[key] = val

    # Parse user choice
    selected_org = None

    # Check for "nouveau" / "new"
    if "nouveau" in user_msg or "new" in user_msg or "créer" in user_msg:
        org_name = ctx.state.get("org_name_query", "")
        return _create_prospect_with_new_org(ctx, org_name)

    # Try to extract a number (#1, le 1, 1, etc.)
    import re
    num_match = re.search(r"#?(\d+)", user_msg)
    if num_match:
        idx = int(num_match.group(1)) - 1  # 0-based
        if 0 <= idx < len(org_results):
            selected_org = org_results[idx]

    # Fallback: first org if message seems affirmative
    if not selected_org and org_results:
        affirmative = any(w in user_msg for w in ["oui", "yes", "ok", "premier", "first", "1"])
        if affirmative:
            selected_org = org_results[0]

    if selected_org:
        ctx.state["org_id"] = selected_org["id"]
        ctx.state["org_name"] = selected_org["name"]
        logger.info("workflow_org_selected", org_id=selected_org["id"], name=selected_org["name"])
        return _create_contact_and_opportunity(ctx)

    # Could not parse selection — ask again
    org_lines = [f"#{i+1} — {o['name']}" for i, o in enumerate(org_results)]
    return ctx.pause(
        message=(
            "Je n'ai pas compris votre choix. Veuillez indiquer le numéro :\n\n"
            + "\n".join(org_lines)
        ),
        resume_key="prospect_org_selected",
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

    items = []
    for i, opp in enumerate(opps, 1):
        tags = [{"label": opp.stage, "icon": "fa-solid fa-layer-group"}]
        if opp.organization_name:
            tags.append({"label": opp.organization_name, "icon": "fa-solid fa-building"})
        items.append({
            "id": str(opp.id), "number": i, "title": opp.name,
            "subtitle": opp.organization_name or "",
            "tags": tags,
            "value": f"{float(opp.amount or 0):,.0f}$",
            "value_label": "Montant",
            "route": f"/opportunities/{opp.id}",
        })

    ctx.emit_action("bob_display",
        display_type="list", title="Top 5 Opportunités",
        subtitle="Triées par montant", icon="fa-solid fa-trophy",
        items=items,
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

    items = []
    for i, opp in enumerate(opps, 1):
        tags = [{"label": opp.stage, "icon": "fa-solid fa-layer-group"}]
        if opp.close_date:
            tags.append({"label": str(opp.close_date), "icon": "fa-solid fa-calendar"})
        items.append({
            "id": str(opp.id), "number": i, "title": opp.name,
            "subtitle": opp.organization_name or "",
            "tags": tags,
            "value": f"{float(opp.amount or 0):,.0f}$" if opp.amount else "—",
            "route": f"/opportunities/{opp.id}",
        })

    ctx.emit_action("bob_display",
        display_type="list", title="À closer ce mois",
        subtitle=f"{now.strftime('%B %Y')}", icon="fa-solid fa-calendar-check",
        items=items,
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

    items = []
    for i, opp in enumerate(opps, 1):
        days_stale = (datetime.utcnow() - opp.updated_at).days if opp.updated_at else 0
        tags = [
            {"label": opp.stage, "icon": "fa-solid fa-layer-group"},
            {"label": f"{days_stale} jours", "icon": "fa-solid fa-clock", "color": "#ef4444"},
        ]
        items.append({
            "id": str(opp.id), "number": i, "title": opp.name,
            "subtitle": opp.organization_name or "",
            "tags": tags,
            "value": f"{float(opp.amount or 0):,.0f}$" if opp.amount else "—",
            "route": f"/opportunities/{opp.id}",
        })

    ctx.emit_action("bob_display",
        display_type="list", title="Deals stagnants",
        subtitle="+30 jours sans mouvement", icon="fa-solid fa-hourglass-half",
        items=items,
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

    stats = []
    total_value = 0.0
    total_count = 0
    for stage, count, value in stats_q:
        val = float(value or 0)
        total_count += count
        total_value += val
        stats.append({
            "label": stage, "value": f"{val:,.0f}$",
            "icon": "fa-solid fa-layer-group",
        })

    stats.insert(0, {
        "label": "Total Pipeline", "value": f"{total_value:,.0f}$",
        "icon": "fa-solid fa-chart-line", "color": "#22c55e",
    })
    stats.insert(1, {
        "label": "Total Deals", "value": str(total_count),
        "icon": "fa-solid fa-handshake",
    })

    ctx.emit_action("bob_display",
        display_type="stats", title="Valeur du Pipeline",
        subtitle="Répartition par étape", icon="fa-solid fa-chart-pie",
        stats=stats,
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

    items = []
    for i, c in enumerate(contacts, 1):
        days = (datetime.utcnow() - c.updated_at).days if c.updated_at else 0
        name = f"{c.first_name or ''} {c.last_name or ''}".strip() or "Sans nom"
        tags = []
        if c.email:
            tags.append({"label": c.email, "icon": "fa-solid fa-envelope"})
        tags.append({"label": f"{days} jours", "icon": "fa-solid fa-clock", "color": "#f59e0b"})
        items.append({
            "id": str(c.id), "number": i, "title": name,
            "subtitle": c.email or "",
            "tags": tags,
            "route": f"/contacts/{c.id}",
        })

    ctx.emit_action("bob_display",
        display_type="list", title="Contacts dormants",
        subtitle="Pas contactés depuis 5+ mois", icon="fa-solid fa-user-clock",
        items=items,
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

    items = []
    for i, c in enumerate(contacts, 1):
        name = f"{c.first_name or ''} {c.last_name or ''}".strip() or "Sans nom"
        tags = []
        if c.email:
            tags.append({"label": c.email, "icon": "fa-solid fa-envelope"})
        if c.phone:
            tags.append({"label": c.phone, "icon": "fa-solid fa-phone"})
        items.append({
            "id": str(c.id), "number": i, "title": name,
            "subtitle": str(c.created_at.date()) if c.created_at else "",
            "tags": tags,
            "route": f"/contacts/{c.id}",
        })

    ctx.emit_action("bob_display",
        display_type="list", title="Contacts récents",
        subtitle="Derniers ajoutés", icon="fa-solid fa-user-plus",
        items=items,
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

    items = []
    for i, c in enumerate(contacts, 1):
        name = f"{c.first_name or ''} {c.last_name or ''}".strip() or "Sans nom"
        tags = [{"label": "Email manquant", "icon": "fa-solid fa-triangle-exclamation", "color": "#ef4444"}]
        if c.phone:
            tags.append({"label": c.phone, "icon": "fa-solid fa-phone"})
        items.append({
            "id": str(c.id), "number": i, "title": name,
            "tags": tags,
            "route": f"/contacts/{c.id}",
        })

    ctx.emit_action("bob_display",
        display_type="list", title="Contacts sans email",
        subtitle="Données incomplètes", icon="fa-solid fa-at",
        items=items,
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

    items = []
    for i, o in enumerate(orgs, 1):
        tags = []
        if o.industry:
            tags.append({"label": o.industry, "icon": "fa-solid fa-building"})
        if o.status:
            tags.append({"label": o.status, "icon": "fa-solid fa-circle"})
        items.append({
            "id": str(o.id), "number": i, "title": o.name,
            "subtitle": o.industry or "",
            "tags": tags,
            "route": f"/organizations/{o.id}",
        })

    ctx.emit_action("bob_display",
        display_type="list", title="Comptes sans opportunité",
        subtitle="Potentiel inexploité", icon="fa-solid fa-building-circle-exclamation",
        items=items,
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

    items = []
    for i, row in enumerate(results, 1):
        tags = [{"label": f"{row.opp_count} opps", "icon": "fa-solid fa-handshake"}]
        if row.industry:
            tags.append({"label": row.industry, "icon": "fa-solid fa-building"})
        items.append({
            "id": str(row.id), "number": i, "title": row.name,
            "tags": tags,
            "value": f"{float(row.total_amount or 0):,.0f}$",
            "value_label": "Total",
            "route": f"/organizations/{row.id}",
        })

    ctx.emit_action("bob_display",
        display_type="list", title="Comptes les plus actifs",
        subtitle="Par nombre d'opportunités", icon="fa-solid fa-fire",
        items=items,
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

    stats = []
    for industry, count in results:
        stats.append({
            "label": industry or "Non spécifié",
            "value": str(count),
            "icon": "fa-solid fa-building",
        })

    ctx.emit_action("bob_display",
        display_type="stats", title="Comptes par industrie",
        subtitle="Répartition", icon="fa-solid fa-chart-bar",
        stats=stats,
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

    items = []
    for i, p in enumerate(products, 1):
        tags = []
        if p.category:
            tags.append({"label": p.category, "icon": "fa-solid fa-tag"})
        if p.sku:
            tags.append({"label": p.sku, "icon": "fa-solid fa-barcode"})
        items.append({
            "id": str(p.id), "number": i, "title": p.name,
            "subtitle": p.category or "",
            "tags": tags,
            "value": f"{float(p.price or 0):,.2f}$" if p.price else "—",
            "value_label": "Prix",
            "route": f"/products/{p.id}",
        })

    ctx.emit_action("bob_display",
        display_type="list", title="Catalogue Produits",
        subtitle=f"{len(products)} produits", icon="fa-solid fa-box",
        items=items,
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

    stats = [
        {"label": "Pipeline actif", "value": f"{total_value:,.0f}$", "icon": "fa-solid fa-chart-line", "color": "#22c55e"},
        {"label": "Deals ouverts", "value": str(total_opps), "icon": "fa-solid fa-handshake"},
        {"label": "Deals stagnants", "value": str(stale_count), "icon": "fa-solid fa-hourglass-half", "color": "#ef4444" if stale_count > 0 else "#22c55e"},
        {"label": "Contacts", "value": str(contact_count), "icon": "fa-solid fa-users"},
        {"label": "Organisations", "value": str(org_count), "icon": "fa-solid fa-building"},
    ]

    ctx.emit_action("bob_display",
        display_type="stats", title="Résumé de votre journée",
        subtitle=now.strftime("%A %d %B %Y"), icon="fa-solid fa-sun",
        stats=stats,
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

    items = []
    for i, a in enumerate(activities, 1):
        type_icons = {
            "CALL": "fa-solid fa-phone",
            "EMAIL": "fa-solid fa-envelope",
            "MEETING": "fa-solid fa-users",
            "TASK": "fa-solid fa-list-check",
            "NOTE": "fa-solid fa-note-sticky",
        }
        status_colors = {
            "PENDING": "#f59e0b",
            "IN_PROGRESS": "#3b82f6",
            "COMPLETED": "#22c55e",
            "CANCELLED": "#6b7280",
        }
        tags = [
            {"label": a.activity_type.value if hasattr(a.activity_type, 'value') else str(a.activity_type),
             "icon": type_icons.get(a.activity_type.value if hasattr(a.activity_type, 'value') else str(a.activity_type), "fa-solid fa-circle")},
            {"label": a.status.value if hasattr(a.status, 'value') else str(a.status),
             "icon": "fa-solid fa-circle",
             "color": status_colors.get(a.status.value if hasattr(a.status, 'value') else str(a.status), "#6b7280")},
        ]
        if a.priority and hasattr(a.priority, 'value') and a.priority.value in ("HIGH", "URGENT"):
            tags.append({"label": a.priority.value, "icon": "fa-solid fa-flag", "color": "#ef4444"})

        items.append({
            "id": str(a.id), "number": i, "title": a.subject,
            "subtitle": a.description[:60] + "..." if a.description and len(a.description) > 60 else (a.description or ""),
            "tags": tags,
            "route": f"/activities",
        })

    completed = sum(1 for a in activities if (a.status.value if hasattr(a.status, 'value') else str(a.status)) == "COMPLETED")
    pending = len(activities) - completed

    ctx.emit_action("bob_display",
        display_type="list", title="Activités du jour",
        subtitle=f"{now.strftime('%A %d %B')} — {completed} complétées, {pending} restantes",
        icon="fa-solid fa-calendar-day",
        items=items,
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

    items = []
    for i, a in enumerate(activities, 1):
        days_overdue = (now - a.due_date).days if a.due_date else 0
        type_icons = {
            "CALL": "fa-solid fa-phone",
            "EMAIL": "fa-solid fa-envelope",
            "MEETING": "fa-solid fa-users",
            "TASK": "fa-solid fa-list-check",
            "NOTE": "fa-solid fa-note-sticky",
        }
        tags = [
            {"label": a.activity_type.value if hasattr(a.activity_type, 'value') else str(a.activity_type),
             "icon": type_icons.get(a.activity_type.value if hasattr(a.activity_type, 'value') else str(a.activity_type), "fa-solid fa-circle")},
            {"label": f"{days_overdue}j en retard", "icon": "fa-solid fa-clock", "color": "#ef4444"},
        ]

        items.append({
            "id": str(a.id), "number": i, "title": a.subject,
            "subtitle": str(a.due_date.date()) if a.due_date else "",
            "tags": tags,
            "route": f"/activities",
        })

    ctx.emit_action("bob_display",
        display_type="list", title="Rappels en retard",
        subtitle=f"{len(activities)} activité(s) en souffrance",
        icon="fa-solid fa-triangle-exclamation",
        items=items,
    )
    ctx.add_tool_step("overdue activities")
    return ctx.complete(message=f"⚠️ **{len(activities)}** activité(s) en retard — à traiter rapidement !")


