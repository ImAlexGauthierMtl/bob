"""Presentation dependencies for Org API."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.use_cases.department_use_cases import DepartmentUseCases
from app.application.use_cases.organization_use_cases import OrganizationUseCases
from app.events.publishers import (
    publish_org_created,
    publish_org_deleted,
    publish_org_updated,
)
from app.infrastructure.database import get_db
from app.infrastructure.persistence.department_repository import DepartmentRepository
from app.infrastructure.persistence.models.department import Department
from app.infrastructure.persistence.models.organization import Organization
from app.infrastructure.persistence.organization_repository import OrganizationRepository


def get_organization_use_cases(db: Session = Depends(get_db)) -> OrganizationUseCases:
    return OrganizationUseCases(
        repo=OrganizationRepository(db),
        create_organization_entity=Organization,
        publish_created=publish_org_created,
        publish_updated=publish_org_updated,
        publish_deleted=publish_org_deleted,
    )


def get_department_use_cases(db: Session = Depends(get_db)) -> DepartmentUseCases:
    return DepartmentUseCases(
        repo=DepartmentRepository(db),
        create_department_entity=Department,
    )
