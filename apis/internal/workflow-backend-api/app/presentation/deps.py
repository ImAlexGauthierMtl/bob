"""Presentation dependencies for Workflow API."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.use_cases.workflow_use_cases import WorkflowUseCases
from app.events.publishers import (
    publish_workflow_created,
    publish_workflow_deleted,
    publish_workflow_executed,
    publish_workflow_updated,
)
from app.infrastructure.database import get_db
from app.infrastructure.persistence.models.workflow import Workflow, WorkflowStep
from app.infrastructure.persistence.models.workflow_execution import WorkflowExecution
from app.infrastructure.persistence.workflow_repository import WorkflowRepository


def get_workflow_use_cases(db: Session = Depends(get_db)) -> WorkflowUseCases:
    return WorkflowUseCases(
        repo=WorkflowRepository(db),
        create_workflow_entity=Workflow,
        create_step_entity=WorkflowStep,
        create_execution_entity=WorkflowExecution,
        publish_workflow_created=publish_workflow_created,
        publish_workflow_updated=publish_workflow_updated,
        publish_workflow_deleted=publish_workflow_deleted,
        publish_workflow_executed=publish_workflow_executed,
    )
