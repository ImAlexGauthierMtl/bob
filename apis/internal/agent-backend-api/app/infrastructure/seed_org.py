"""Seed script — ensures a default BCC organization exists for the master tenant."""
from sqlalchemy.orm import Session
from shared.infrastructure import get_logger
from app.domain.entities.bcc_entities import BccOrganization, BccOrgProfile

logger = get_logger(__name__)

MASTER_TENANT_ID = "default"
DEFAULT_ORG_NAME = "Croo Digital"
DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"


def seed_default_organization(db: Session) -> None:
    existing = db.query(BccOrganization).filter(
        BccOrganization.id == DEFAULT_ORG_ID,
    ).first()
    if existing:
        logger.info("seed_org.exists", org_id=existing.id, name=existing.name)
        return

    org = BccOrganization(
        id=DEFAULT_ORG_ID,
        tenant_id=MASTER_TENANT_ID,
        name=DEFAULT_ORG_NAME,
        description="Master tenant organization",
        created_by="system-seed",
    )
    db.add(org)
    db.flush()

    profile = BccOrgProfile(
        organization_id=org.id,
        tenant_id=MASTER_TENANT_ID,
        created_by="system-seed",
    )
    db.add(profile)
    db.commit()
    logger.info("seed_org.created", org_id=org.id, name=org.name)
