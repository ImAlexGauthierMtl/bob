"""Presentation dependencies for Email API."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.use_cases.integration_settings_use_cases import IntegrationSettingsUseCases
from app.application.use_cases.membrane_crud_use_cases import MembraneCrudUseCases
from app.application.use_cases.ms365_core_use_cases import MS365CoreUseCases
from app.application.use_cases.smart_label_use_cases import SmartLabelUseCases
from app.events.publishers import publish_email_received
from app.infrastructure.database import get_db
from app.infrastructure.persistence.integration_settings_repository import IntegrationSettingsRepository
from app.infrastructure.persistence.membrane_repository import MembraneRepository
from app.infrastructure.persistence.models.smart_label import SmartLabel
from app.infrastructure.persistence.ms365_repository import MS365Repository
from app.infrastructure.persistence.smart_label_repository import SmartLabelRepository


def get_ms365_core_use_cases(db: Session = Depends(get_db)) -> MS365CoreUseCases:
    return MS365CoreUseCases(
        repo=MS365Repository(db),
        publish_email_received=publish_email_received,
    )


def get_membrane_crud_use_cases(db: Session = Depends(get_db)) -> MembraneCrudUseCases:
    return MembraneCrudUseCases(repo=MembraneRepository(db))


def get_smart_label_use_cases(db: Session = Depends(get_db)) -> SmartLabelUseCases:
    return SmartLabelUseCases(
        repo=SmartLabelRepository(db),
        create_label=SmartLabel,
    )


def get_integration_settings_use_cases(db: Session = Depends(get_db)) -> IntegrationSettingsUseCases:
    return IntegrationSettingsUseCases(repo=IntegrationSettingsRepository(db))
