"""Presentation dependencies for Agent API."""
from uuid import uuid4

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.use_cases.bcc_use_cases import BccUseCases
from app.application.use_cases.bob_settings_use_cases import BobSettingsUseCases
from app.application.use_cases.behavioral_analysis_use_cases import BehavioralAnalysisUseCases
from app.application.use_cases.capability_use_cases import CapabilityUseCases
from app.application.use_cases.client_map_use_cases import ClientMapUseCases
from app.application.use_cases.training_use_cases import TrainingUseCases
from app.infrastructure.persistence.bob_settings_repository import BobSettingsRepository
from app.infrastructure.database import get_db
from app.infrastructure.llm_behavioral_profile_provider import GroqBehavioralProfileProvider
from app.infrastructure.persistence.capability_repository import CapabilityRepository
from app.infrastructure.persistence.client_map_repository import ClientMapRepository
from app.infrastructure.persistence.models.training_models import TrainingMissingElement, TrainingNote, TrainingSession
from app.infrastructure.persistence.training_repository import TrainingRepository
from app.presentation.bcc_operations import BccOperations


def get_bcc_use_cases(db: Session = Depends(get_db)) -> BccUseCases:
    return BccUseCases(operations=BccOperations(db))


def get_capability_use_cases(db: Session = Depends(get_db)) -> CapabilityUseCases:
    return CapabilityUseCases(repo=CapabilityRepository(db))


def get_bob_settings_use_cases(db: Session = Depends(get_db)) -> BobSettingsUseCases:
    return BobSettingsUseCases(repo=BobSettingsRepository(db))


def get_client_map_use_cases(db: Session = Depends(get_db)) -> ClientMapUseCases:
    return ClientMapUseCases(repo=ClientMapRepository(db))


def get_behavioral_analysis_use_cases(db: Session = Depends(get_db)) -> BehavioralAnalysisUseCases:
    return BehavioralAnalysisUseCases(
        repo=ClientMapRepository(db),
        provider=GroqBehavioralProfileProvider(),
    )


def get_training_use_cases(db: Session = Depends(get_db)) -> TrainingUseCases:
    return TrainingUseCases(
        repo=TrainingRepository(db),
        create_session_entity=TrainingSession,
        create_note_entity=TrainingNote,
        create_missing_entity=TrainingMissingElement,
        create_id=lambda: str(uuid4()),
    )
