"""CRM Context Loader — loads live CRM data snapshot for the advisor.

Queries the CRM database to build a real-time business context
that gets injected alongside the BCC organizational context.

Provides:
  - Pipeline snapshot (total deals, value, stages)
  - Top accounts (by opportunity value)
  - Recent activities (last 7 days)
  - Contact stats
  - Quick KPIs
"""

import structlog
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)


def load_crm_context(
    db: Session,
    tenant_id: str,
    user_id: str = "",
) -> str:
    """Load live CRM data snapshot for the advisor.

    Args:
        db: SQLAlchemy session.
        tenant_id: Tenant ID to scope queries.
        user_id: User ID for user-specific data.

    Returns:
        Formatted text block to inject into the advisor system prompt.
    """
    from app.domain.entities.organization import Organization
    from app.domain.entities.contact import Contact
    from app.domain.entities.opportunity import Opportunity
    from app.domain.entities.activity import Activity

    sections: list[str] = []
    sections.append("\n## 📊 CRM Data Snapshot (Live)")

    try:
        # ── Pipeline Overview ────────────────────────────────────
        total_opps = db.query(func.count(Opportunity.id)).filter(
            Opportunity.tenant_id == tenant_id,
        ).scalar() or 0

        total_value = db.query(func.sum(Opportunity.amount)).filter(
            Opportunity.tenant_id == tenant_id,
        ).scalar() or 0

        if total_opps > 0:
            # Stage breakdown
            stage_data = db.query(
                Opportunity.stage,
                func.count(Opportunity.id),
                func.sum(Opportunity.amount),
            ).filter(
                Opportunity.tenant_id == tenant_id,
            ).group_by(Opportunity.stage).all()

            sections.append(f"**Pipeline**: {total_opps} deal(s), {total_value:,.0f}$ total")
            if stage_data:
                stage_lines = []
                for stage, count, value in stage_data:
                    stage_lines.append(f"  - {stage or 'N/A'}: {count} ({value or 0:,.0f}$)")
                sections.append("\n".join(stage_lines))

        # ── Organization Stats ───────────────────────────────────
        total_orgs = db.query(func.count(Organization.id)).filter(
            Organization.tenant_id == tenant_id,
        ).scalar() or 0

        sections.append(f"**Accounts**: {total_orgs} total")

        # Top 5 accounts by opportunity value
        if total_opps > 0:
            top_accounts = db.query(
                Organization.name,
                func.sum(Opportunity.amount).label("total_value"),
                func.count(Opportunity.id).label("deal_count"),
            ).join(
                Opportunity, Opportunity.organization_id == Organization.id,
            ).filter(
                Organization.tenant_id == tenant_id,
            ).group_by(
                Organization.name,
            ).order_by(
                desc("total_value"),
            ).limit(5).all()

            if top_accounts:
                sections.append("**Top Accounts (by pipeline value)**:")
                for name, value, count in top_accounts:
                    sections.append(f"  - {name}: {value or 0:,.0f}$ ({count} deal(s))")

        # ── Contact Stats ────────────────────────────────────────
        total_contacts = db.query(func.count(Contact.id)).filter(
            Contact.tenant_id == tenant_id,
        ).scalar() or 0

        sections.append(f"**Contacts**: {total_contacts} total")

        # ── Recent Activity (7 days) ─────────────────────────────
        week_ago = datetime.utcnow() - timedelta(days=7)
        try:
            recent_activities = db.query(func.count(Activity.id)).filter(
                Activity.tenant_id == tenant_id,
                Activity.created_at >= week_ago,
            ).scalar() or 0
            sections.append(f"**Activities (7 days)**: {recent_activities}")
        except Exception:
            pass  # Activity model may not be fully set up

        # ── Accounts by Status ───────────────────────────────────
        status_data = db.query(
            Organization.status,
            func.count(Organization.id),
        ).filter(
            Organization.tenant_id == tenant_id,
            Organization.status.isnot(None),
            Organization.status != "",
        ).group_by(Organization.status).all()

        if status_data:
            sections.append("**Accounts by Status**:")
            for status, count in status_data:
                sections.append(f"  - {status}: {count}")

    except Exception as e:
        logger.warning("crm_context_load_error", error=str(e))
        sections.append("*(CRM data temporarily unavailable)*")

    context_text = "\n".join(sections)

    logger.info(
        "crm_context_loaded",
        tenant_id=tenant_id,
        sections_count=len(sections),
        context_length=len(context_text),
    )

    return context_text
