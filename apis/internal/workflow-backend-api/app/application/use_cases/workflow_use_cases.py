"""Workflow application use cases."""
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Protocol

from app.domain.exceptions import (
    WorkflowExecutionNotFoundError,
    WorkflowNotFoundError,
    WorkflowStepNotFoundError,
)


WorkflowEntity = Any
WorkflowStepEntity = Any
WorkflowExecutionEntity = Any
WorkflowFactory = Callable[..., WorkflowEntity]
WorkflowStepFactory = Callable[..., WorkflowStepEntity]
WorkflowExecutionFactory = Callable[..., WorkflowExecutionEntity]
WorkflowPublisher = Callable[[str, dict[str, Any]], Awaitable[None]]
WorkflowDeletedPublisher = Callable[[str], Awaitable[None]]
WorkflowExecutedPublisher = Callable[[str, str, dict[str, Any]], Awaitable[None]]


class WorkflowRepositoryPort(Protocol):
    def create(self, wf: WorkflowEntity) -> WorkflowEntity:
        ...

    def get_by_id(self, wf_id: str, tenant_id: str) -> Optional[WorkflowEntity]:
        ...

    def list_all(
        self,
        tenant_id: str,
        level: Optional[str] = None,
        module: Optional[str] = None,
        is_template: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[WorkflowEntity]:
        ...

    def count(self, tenant_id: str, level: Optional[str] = None) -> int:
        ...

    def update(self, wf: WorkflowEntity) -> WorkflowEntity:
        ...

    def soft_delete(self, wf: WorkflowEntity, deleted_by: str) -> WorkflowEntity:
        ...

    def add_step(self, step: WorkflowStepEntity) -> WorkflowStepEntity:
        ...

    def get_steps(self, workflow_id: str) -> list[WorkflowStepEntity]:
        ...

    def get_step_by_id(self, step_id: str) -> Optional[WorkflowStepEntity]:
        ...

    def update_step(self, step: WorkflowStepEntity) -> WorkflowStepEntity:
        ...

    def delete_step(self, step_id: str) -> None:
        ...

    def create_execution(self, exe: WorkflowExecutionEntity) -> WorkflowExecutionEntity:
        ...

    def get_execution(self, exe_id: str) -> Optional[WorkflowExecutionEntity]:
        ...

    def list_executions(self, workflow_id: str, limit: int = 20) -> list[WorkflowExecutionEntity]:
        ...

    def update_execution(self, exe: WorkflowExecutionEntity) -> WorkflowExecutionEntity:
        ...

    def get_step_executions(self, execution_id: str) -> list[Any]:
        ...

    def get_monitoring_stats(self, tenant_id: str) -> dict[str, Any]:
        ...

    def list_recent_executions(
        self,
        tenant_id: str,
        limit: int = 20,
        status_filter: Optional[str] = None,
    ) -> list[WorkflowExecutionEntity]:
        ...


@dataclass(frozen=True)
class WorkflowWithSteps:
    workflow: WorkflowEntity
    steps: list[WorkflowStepEntity]


@dataclass(frozen=True)
class WorkflowListResult:
    items: list[WorkflowWithSteps]
    total: int
    skip: int
    limit: int


@dataclass(frozen=True)
class ExecutionDetailResult:
    execution: WorkflowExecutionEntity
    steps: list[Any]


class WorkflowUseCases:
    def __init__(
        self,
        repo: WorkflowRepositoryPort,
        create_workflow_entity: WorkflowFactory,
        create_step_entity: WorkflowStepFactory,
        create_execution_entity: WorkflowExecutionFactory,
        publish_workflow_created: WorkflowPublisher,
        publish_workflow_updated: WorkflowPublisher,
        publish_workflow_deleted: WorkflowDeletedPublisher,
        publish_workflow_executed: WorkflowExecutedPublisher,
    ) -> None:
        self.repo = repo
        self.create_workflow_entity = create_workflow_entity
        self.create_step_entity = create_step_entity
        self.create_execution_entity = create_execution_entity
        self.publish_workflow_created = publish_workflow_created
        self.publish_workflow_updated = publish_workflow_updated
        self.publish_workflow_deleted = publish_workflow_deleted
        self.publish_workflow_executed = publish_workflow_executed

    async def create_workflow(self, data: dict[str, Any], user: dict[str, Any]) -> WorkflowWithSteps:
        step_inputs = data.pop("steps", None) or []
        workflow = self.create_workflow_entity(
            name=data["name"],
            description=data.get("description"),
            level=data.get("level", "company"),
            owner_id=data.get("owner_id") or user.get("user_id"),
            owner_type=data.get("owner_type") or "user",
            trigger_type=data.get("trigger_type", "manual"),
            trigger_config=data.get("trigger_config"),
            execution_mode=data.get("execution_mode", "suggest"),
            required_capabilities=data.get("required_capabilities"),
            is_overridable=data.get("is_overridable", True),
            override_policy=data.get("override_policy", "choice"),
            overrides_workflow_id=data.get("overrides_workflow_id"),
            module=data.get("module"),
            category=data.get("category"),
            is_template=data.get("is_template", False),
            tenant_id=user["tenant_id"],
            created_by=user["email"],
        )
        workflow = self.repo.create(workflow)

        for step_data in step_inputs:
            self.repo.add_step(self._build_step(workflow.id, step_data))

        steps = self.repo.get_steps(workflow.id)
        await self.publish_workflow_created(
            workflow.id,
            {"name": workflow.name, "tenant_id": workflow.tenant_id},
        )
        return WorkflowWithSteps(workflow, steps)

    async def list_workflows(
        self,
        tenant_id: str,
        level: Optional[str],
        module: Optional[str],
        is_template: Optional[bool],
        skip: int,
        limit: int,
    ) -> WorkflowListResult:
        workflows = self.repo.list_all(tenant_id, level, module, is_template, skip, limit)
        return WorkflowListResult(
            items=[WorkflowWithSteps(wf, self.repo.get_steps(wf.id)) for wf in workflows],
            total=self.repo.count(tenant_id, level),
            skip=skip,
            limit=limit,
        )

    async def get_workflow(self, wf_id: str, tenant_id: str) -> WorkflowWithSteps:
        workflow = self.repo.get_by_id(wf_id, tenant_id)
        if not workflow:
            raise WorkflowNotFoundError
        return WorkflowWithSteps(workflow, self.repo.get_steps(workflow.id))

    async def update_workflow(
        self,
        wf_id: str,
        updates: dict[str, Any],
        user: dict[str, Any],
    ) -> WorkflowWithSteps:
        workflow = self.repo.get_by_id(wf_id, user["tenant_id"])
        if not workflow:
            raise WorkflowNotFoundError

        for key, value in updates.items():
            setattr(workflow, key, value)
        workflow.updated_by = user["email"]
        workflow = self.repo.update(workflow)
        await self.publish_workflow_updated(workflow.id, {"fields": list(updates.keys())})
        return WorkflowWithSteps(workflow, self.repo.get_steps(workflow.id))

    async def delete_workflow(self, wf_id: str, user: dict[str, Any]) -> None:
        workflow = self.repo.get_by_id(wf_id, user["tenant_id"])
        if not workflow:
            raise WorkflowNotFoundError
        self.repo.soft_delete(workflow, user["email"])
        await self.publish_workflow_deleted(wf_id)

    async def list_steps(self, wf_id: str, user: dict[str, Any]) -> list[WorkflowStepEntity]:
        workflow = self.repo.get_by_id(wf_id, user["tenant_id"])
        if not workflow:
            raise WorkflowNotFoundError
        return self.repo.get_steps(wf_id)

    async def add_step(
        self,
        wf_id: str,
        data: dict[str, Any],
        user: dict[str, Any],
    ) -> WorkflowStepEntity:
        workflow = self.repo.get_by_id(wf_id, user["tenant_id"])
        if not workflow:
            raise WorkflowNotFoundError
        return self.repo.add_step(self._build_step(wf_id, data))

    async def update_step(self, wf_id: str, step_id: str, updates: dict[str, Any]) -> WorkflowStepEntity:
        step = self.repo.get_step_by_id(step_id)
        if not step or step.workflow_id != wf_id:
            raise WorkflowStepNotFoundError
        for key, value in updates.items():
            setattr(step, key, value)
        return self.repo.update_step(step)

    async def delete_step(self, wf_id: str, step_id: str) -> None:
        step = self.repo.get_step_by_id(step_id)
        if not step or step.workflow_id != wf_id:
            raise WorkflowStepNotFoundError
        self.repo.delete_step(step_id)

    async def create_execution(
        self,
        wf_id: str,
        data: dict[str, Any],
        user: dict[str, Any],
    ) -> WorkflowExecutionEntity:
        workflow = self.repo.get_by_id(wf_id, user["tenant_id"])
        if not workflow:
            raise WorkflowNotFoundError

        steps = self.repo.get_steps(wf_id)
        execution = self.create_execution_entity(
            workflow_id=wf_id,
            triggered_by=user["email"],
            trigger_type="manual",
            input_data=data.get("input_data"),
            steps_total=len(steps),
            tenant_id=user["tenant_id"],
        )
        created = self.repo.create_execution(execution)
        await self.publish_workflow_executed(wf_id, created.id, {"triggered_by": user["email"]})
        return created

    async def list_executions(self, wf_id: str, limit: int) -> list[WorkflowExecutionEntity]:
        return self.repo.list_executions(wf_id, limit)

    async def get_execution_detail(self, wf_id: str, exe_id: str) -> ExecutionDetailResult:
        execution = self.repo.get_execution(exe_id)
        if not execution or execution.workflow_id != wf_id:
            raise WorkflowExecutionNotFoundError
        return ExecutionDetailResult(execution, self.repo.get_step_executions(exe_id))

    async def update_execution(
        self,
        wf_id: str,
        exe_id: str,
        updates: dict[str, Any],
    ) -> WorkflowExecutionEntity:
        execution = self.repo.get_execution(exe_id)
        if not execution or execution.workflow_id != wf_id:
            raise WorkflowExecutionNotFoundError

        for key, value in updates.items():
            if hasattr(execution, key):
                setattr(execution, key, value)
        return self.repo.update_execution(execution)

    async def get_monitoring_stats(self, tenant_id: str) -> dict[str, Any]:
        return self.repo.get_monitoring_stats(tenant_id)

    async def get_recent_executions(
        self,
        tenant_id: str,
        limit: int,
        status_filter: Optional[str],
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": execution.id,
                "workflow_id": execution.workflow_id,
                "status": execution.status,
                "triggered_by": execution.triggered_by,
                "steps_completed": execution.steps_completed,
                "steps_total": execution.steps_total,
                "duration_ms": execution.duration_ms,
                "error": execution.error,
                "started_at": str(execution.started_at) if execution.started_at else None,
                "completed_at": str(execution.completed_at) if execution.completed_at else None,
            }
            for execution in self.repo.list_recent_executions(tenant_id, limit, status_filter)
        ]

    def _build_step(self, workflow_id: str, data: dict[str, Any]) -> WorkflowStepEntity:
        return self.create_step_entity(
            workflow_id=workflow_id,
            name=data["name"],
            step_order=data.get("step_order", 0),
            step_type=data["step_type"],
            agent_node=data.get("agent_node"),
            config=data.get("config"),
            on_success=data.get("on_success"),
            on_failure=data.get("on_failure"),
            description=data.get("description"),
            is_entry_point=data.get("is_entry_point", False),
        )
