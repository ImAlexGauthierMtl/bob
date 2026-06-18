"""Presentation dependencies for Contact API."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.use_cases.contact_use_cases import ContactUseCases
from app.events.publishers import (
    publish_contact_created,
    publish_contact_deleted,
    publish_contact_updated,
)
from app.infrastructure.database import get_db
from app.infrastructure.persistence.contact_repository import ContactRepository
from app.infrastructure.persistence.models.contact import Contact


def get_contact_use_cases(db: Session = Depends(get_db)) -> ContactUseCases:
    return ContactUseCases(
        repo=ContactRepository(db),
        create_contact_entity=Contact,
        publish_created=publish_contact_created,
        publish_updated=publish_contact_updated,
        publish_deleted=publish_contact_deleted,
    )
