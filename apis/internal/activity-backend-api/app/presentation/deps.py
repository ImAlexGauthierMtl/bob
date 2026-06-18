"""Presentation dependencies for Activity API."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.use_cases.activity_use_cases import ActivityUseCases
from app.events.publishers import publish_activity_created, publish_activity_updated
from app.infrastructure.database import get_db
from app.infrastructure.persistence.activity_repository import ActivityRepository


def get_activity_use_cases(db: Session = Depends(get_db)) -> ActivityUseCases:
    return ActivityUseCases(
        repo=ActivityRepository(db),
        publish_created=publish_activity_created,
        publish_updated=publish_activity_updated,
    )
