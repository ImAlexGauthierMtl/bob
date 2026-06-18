"""Presentation dependencies for Email API."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.use_cases.integration_settings_use_cases import IntegrationSettingsUseCases
from app.application.use_cases.membrane_crud_use_cases import MembraneCrudUseCases
from app.application.use_cases.ms365_core_use_cases import MS365CoreUseCases
from app.application.use_cases.pipedream_provider_use_cases import PipedreamProviderUseCases
from app.application.use_cases.smart_label_use_cases import SmartLabelUseCases
from app.application.services.membrane_tenant_key_service import build_tenant_key, default_scope_for
from app.events.publishers import publish_email_received
from app.infrastructure.database import get_db
from app.infrastructure.clients_email_backend import integration_settings_client
from app.infrastructure.external.pipedream_service import (
    PipedreamClient,
    set_pipedream_credentials,
    _get_settings as get_pipedream_settings,
)
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


async def _lookup_integration_setting(integration_key: str, request_headers=None):
    try:
        return await integration_settings_client.get(integration_key, forward_headers=request_headers)
    except Exception:
        return None


def get_pipedream_provider_use_cases() -> PipedreamProviderUseCases:
    return PipedreamProviderUseCases(
        client_factory=PipedreamClient,
        setting_lookup=_lookup_integration_setting,
        build_external_user_id=build_tenant_key,
        default_scope_for=default_scope_for,
        get_settings=get_pipedream_settings,
        set_credentials=set_pipedream_credentials,
    )
