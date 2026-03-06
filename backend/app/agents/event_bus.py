"""Event bus — lightweight in-process event dispatcher.

Publishes domain events and triggers matching workflows automatically.
Events follow the pattern: "entity.action" (e.g., "contact.created").
"""

import asyncio
from typing import Any, Callable, Awaitable

import structlog
from sqlalchemy.orm import Session

from app.domain.entities.workflow import Workflow
from app.infrastructure.persistence.workflow_repository import WorkflowRepository
from app.infrastructure.persistence.user_repository import UserRepository
from app.agents.workflow_runner import WorkflowRunner

logger = structlog.get_logger(__name__)


class EventBus:
    """In-process event bus that triggers matching workflows."""

    async def publish(
        self,
        event_name: str,
        payload: dict[str, Any],
        db: Session,
        tenant_id: str,
        triggered_by: str = "system",
    ) -> list[str]:
        """Publish an event and trigger all matching workflows.

        Args:
            event_name: Event identifier (e.g., "contact.created")
            payload: Event data to pass as workflow input
            db: Database session
            tenant_id: Tenant scope
            triggered_by: User email or "system"

        Returns:
            List of execution IDs for triggered workflows
        """
        logger.info("event_published", event=event_name, tenant=tenant_id)

        # Find all active workflows that match this event
        repo = WorkflowRepository(db)
        matching = self._find_matching_workflows(repo, event_name, tenant_id)

        if not matching:
            logger.debug("event_no_matching_workflows", event=event_name)
            return []

        logger.info("event_matching_workflows", event=event_name, count=len(matching))

        # Get the triggering user (or first admin)
        user_repo = UserRepository(db)
        user = user_repo.get_by_email(triggered_by)
        if not user:
            # Fallback: use first user in tenant
            from app.domain.entities.user import User
            user = db.query(User).filter(
                User.tenant_id == tenant_id,
                User.is_deleted == False,
            ).first()

        if not user:
            logger.error("event_no_user_found", event=event_name, tenant=tenant_id)
            return []

        # Execute matching workflows
        runner = WorkflowRunner(db)
        execution_ids = []

        for wf in matching:
            try:
                execution = await runner.run(
                    workflow=wf,
                    user=user,
                    tenant_id=tenant_id,
                    input_data={"event": event_name, **payload},
                    triggered_by=triggered_by,
                )
                execution_ids.append(execution.id)
                logger.info(
                    "event_workflow_triggered",
                    event=event_name,
                    workflow=wf.name,
                    execution_id=execution.id,
                    status=execution.status,
                )
            except (PermissionError, ValueError) as e:
                logger.warning(
                    "event_workflow_skipped",
                    event=event_name,
                    workflow=wf.name,
                    reason=str(e),
                )

        return execution_ids

    def _find_matching_workflows(
        self,
        repo: WorkflowRepository,
        event_name: str,
        tenant_id: str,
    ) -> list[Workflow]:
        """Find workflows whose trigger_config matches the event.

        Supports:
        - Exact match: "contact.created" == "contact.created"
        - Wildcard: "*.created" matches "contact.created"
        - Wildcard: "contact.*" matches "contact.created"
        """
        # Get all active event-triggered workflows
        all_workflows = repo.list_all(tenant_id, skip=0, limit=500)
        matching = []

        for wf in all_workflows:
            if not wf.is_active:
                continue
            if wf.trigger_type != "event":
                continue
            if not wf.trigger_config:
                continue

            trigger_event = wf.trigger_config.get("event", "")
            if self._event_matches(trigger_event, event_name):
                matching.append(wf)

        return matching

    @staticmethod
    def _event_matches(pattern: str, event_name: str) -> bool:
        """Check if an event pattern matches an event name.

        Supports wildcards (*) for single segment matching.
        """
        if pattern == event_name:
            return True

        pattern_parts = pattern.split(".")
        event_parts = event_name.split(".")

        if len(pattern_parts) != len(event_parts):
            return False

        for p, e in zip(pattern_parts, event_parts):
            if p == "*":
                continue
            if p != e:
                return False

        return True


# Singleton instance
event_bus = EventBus()
