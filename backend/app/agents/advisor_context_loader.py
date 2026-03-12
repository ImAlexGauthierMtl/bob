"""Advisor Context Loader — loads BCC organizational knowledge for the advisor.

Queries the BCC tables to build a comprehensive organizational context
that gets injected into the Kimi K2.5 system prompt. Includes:
  - Organization profile (name, location, domains)
  - Profile entries (vision, mission, culture, competition, methodology)
  - Regulations (CASL, Loi 25, etc.)
  - Industries + best practices
  - User's role, KPIs, and context
"""

import structlog
from sqlalchemy.orm import Session

from app.domain.entities.bcc_entities import (
    BccOrganization,
    BccOrgProfile,
    BccProfileEntry,
    BccRegulation,
    BccIndustry,
    BccOrgIndustry,
    BccUserRole,
    BccRole,
    BccDepartment,
    BccTeam,
)

logger = structlog.get_logger(__name__)

# Sections to load from profile entries (priority order)
_ADVISOR_SECTIONS = [
    "vision",
    "mission",
    "culture",
    "competition",
    "methodology",
    "best_practices",
    "market_trends",
    "deliverables",
    "kpis",
    "stack",
    "sop",
]


def load_advisor_context(
    db: Session,
    tenant_id: str,
    user_id: str = "",
) -> str:
    """Load BCC organizational context for the business advisor.

    Args:
        db: SQLAlchemy session.
        tenant_id: Tenant ID to scope queries.
        user_id: User ID for role-specific context.

    Returns:
        Formatted text block to inject into the advisor system prompt.
    """
    sections: list[str] = []

    # ── Organization Profile ──────────────────────────────────
    org = (
        db.query(BccOrganization)
        .filter(BccOrganization.tenant_id == tenant_id)
        .first()
    )
    if org:
        sections.append(f"## Organization: {org.name}")
        if org.description:
            sections.append(org.description)

        profile: BccOrgProfile | None = org.profile
        if profile:
            location_parts = [p for p in [profile.city, profile.state_province, profile.country] if p]
            if location_parts:
                sections.append(f"Location: {', '.join(location_parts)}")
            if profile.operations_domains:
                sections.append(f"Domains: {', '.join(profile.operations_domains)}")

    # ── Profile Entries (vision, mission, culture, etc.) ──────
    entries = (
        db.query(BccProfileEntry)
        .filter(
            BccProfileEntry.tenant_id == tenant_id,
            BccProfileEntry.is_active.is_(True),
            BccProfileEntry.section.in_(_ADVISOR_SECTIONS),
        )
        .order_by(BccProfileEntry.section, BccProfileEntry.version.desc())
        .all()
    )

    # Group by section, take latest version only
    seen_sections: set[str] = set()
    for entry in entries:
        key = f"{entry.entity_type}:{entry.entity_id}:{entry.section}:{entry.perspective}"
        if key in seen_sections:
            continue
        seen_sections.add(key)

        header = entry.section.replace("_", " ").title()
        if entry.perspective != "general":
            header += f" ({entry.perspective})"

        sections.append(f"\n### {header}")
        if entry.content:
            sections.append(entry.content)
        if entry.structured_data:
            for k, v in entry.structured_data.items():
                if isinstance(v, list):
                    sections.append(f"- **{k}**: {', '.join(str(x) for x in v)}")
                else:
                    sections.append(f"- **{k}**: {v}")

    # ── Regulations ───────────────────────────────────────────
    if org and org.profile:
        regulations = (
            db.query(BccRegulation)
            .filter(BccRegulation.profile_id == org.profile.id)
            .all()
        )
        if regulations:
            sections.append("\n### Regulatory Environment")
            for reg in regulations:
                line = f"- **{reg.name}** ({reg.type}, {reg.enforcement_level})"
                if reg.description:
                    line += f": {reg.description}"
                sections.append(line)

    # ── Industries ────────────────────────────────────────────
    if org:
        industry_links = (
            db.query(BccOrgIndustry)
            .filter(BccOrgIndustry.organization_id == org.id)
            .all()
        )
        if industry_links:
            industries = []
            for link in industry_links:
                ind = db.query(BccIndustry).filter(BccIndustry.id == link.industry_id).first()
                if ind:
                    industries.append(ind.name)
                    if ind.best_practices:
                        sections.append(f"\n### Industry Best Practices: {ind.name}")
                        for k, v in ind.best_practices.items():
                            sections.append(f"- {k}: {v}")
            if industries:
                sections.append(f"\nIndustries: {', '.join(industries)}")

    # ── User Role & Context ───────────────────────────────────
    if user_id:
        user_role = (
            db.query(BccUserRole)
            .filter(
                BccUserRole.tenant_id == tenant_id,
                BccUserRole.user_id == user_id,
            )
            .first()
        )
        if user_role:
            role = db.query(BccRole).filter(BccRole.id == user_role.role_id).first()
            if role:
                sections.append(f"\n### Your Role: {role.name}")
                if role.description:
                    sections.append(role.description)
                if role.kpis:
                    sections.append("**KPIs:**")
                    for k, v in role.kpis.items():
                        sections.append(f"- {k}: {v}")
                if role.context:
                    for k, v in role.context.items():
                        sections.append(f"- {k}: {v}")

                # Team and department context
                if role.team_id:
                    team = db.query(BccTeam).filter(BccTeam.id == role.team_id).first()
                    if team:
                        sections.append(f"Team: {team.name}")
                        dept = db.query(BccDepartment).filter(BccDepartment.id == team.department_id).first()
                        if dept:
                            sections.append(f"Department: {dept.name}")

    context_text = "\n".join(sections)

    logger.info(
        "advisor_context_loaded",
        tenant_id=tenant_id,
        sections_count=len(sections),
        context_length=len(context_text),
    )

    return context_text
