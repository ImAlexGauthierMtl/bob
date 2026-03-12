"""Dependency guard — prevents deletion of entities with active children.

Reusable utility that checks for child dependencies before allowing
soft-delete or hard-delete operations. Returns a list of blocking
dependencies with counts.
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.entities.organization import Organization
from app.domain.entities.contact import Contact
from app.domain.entities.opportunity import Opportunity
from app.domain.entities.quote import Quote
from app.domain.entities.activity import Activity


# Map of parent entity → list of (child entity class, FK column name, label)
DEPENDENCY_MAP: dict[str, list[tuple[type, str, str]]] = {
    "organizations": [
        (Contact, "organization_id", "contacts"),
        (Opportunity, "organization_id", "opportunities"),
        (Quote, "organization_id", "quotes"),
        (Activity, "organization_id", "activities"),
    ],
    "contacts": [
        (Opportunity, "contact_id", "opportunities"),
        (Activity, "contact_id", "activities"),
    ],
    "opportunities": [
        (Quote, "opportunity_id", "quotes"),
        (Activity, "opportunity_id", "activities"),
    ],
}


def check_dependencies(
    db: Session,
    entity_table: str,
    entity_id: str,
    tenant_id: str,
) -> list[dict[str, int | str]]:
    """Check if an entity has active (non-deleted) child dependencies.

    Args:
        db: Database session
        entity_table: Table name of the parent entity (e.g. "organizations")
        entity_id: ID of the parent entity
        tenant_id: Tenant ID for scoping

    Returns:
        List of dicts with 'entity' and 'count' for each blocking dependency.
        Empty list means safe to delete.
    """
    blockers: list[dict[str, int | str]] = []

    deps = DEPENDENCY_MAP.get(entity_table, [])
    for child_cls, fk_col, label in deps:
        query = db.query(child_cls).filter(
            getattr(child_cls, fk_col) == entity_id,
        )
        # Respect soft-delete: only count non-deleted children
        if hasattr(child_cls, "is_deleted"):
            query = query.filter(child_cls.is_deleted == False)  # noqa: E712
        # Respect tenant isolation
        if hasattr(child_cls, "tenant_id"):
            query = query.filter(child_cls.tenant_id == tenant_id)

        count = query.count()
        if count > 0:
            blockers.append({"entity": label, "count": count})

    return blockers


def guard_delete(
    db: Session,
    entity_table: str,
    entity_id: str,
    tenant_id: str,
) -> None:
    """Raise HTTP 409 Conflict if entity has active child dependencies.

    Usage in routes/use cases:
        guard_delete(db, "organizations", org_id, tenant_id)
    """
    blockers = check_dependencies(db, entity_table, entity_id, tenant_id)
    if blockers:
        details = ", ".join(
            f"{b['count']} {b['entity']}" for b in blockers
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete: {details} still linked. Remove or reassign them first.",
        )
