"""Workflow repository — data access layer."""

from typing import Optional, List
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.workflow import Workflow, WorkflowStep
from app.infrastructure.persistence.models.workflow_execution import WorkflowExecution, WorkflowStepExecution


class WorkflowRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Workflow CRUD ─────────────────────────

    def create(self, wf: Workflow) -> Workflow:
        self.db.add(wf)
        self.db.commit()
        self.db.refresh(wf)
        return wf

    def get_by_id(self, wf_id: str, tenant_id: str) -> Optional[Workflow]:
        return self.db.query(Workflow).filter(
            Workflow.id == wf_id,
            Workflow.tenant_id == tenant_id,
            Workflow.is_deleted == False,
        ).first()

    def list_all(
        self,
        tenant_id: str,
        level: Optional[str] = None,
        module: Optional[str] = None,
        is_template: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Workflow]:
        query = self.db.query(Workflow).filter(
            Workflow.tenant_id == tenant_id,
            Workflow.is_deleted == False,
        )
        if level:
            query = query.filter(Workflow.level == level)
        if module:
            query = query.filter(Workflow.module == module)
        if is_template is not None:
            query = query.filter(Workflow.is_template == is_template)
        return query.order_by(Workflow.name).offset(skip).limit(limit).all()

    def count(self, tenant_id: str, level: Optional[str] = None) -> int:
        query = self.db.query(Workflow).filter(
            Workflow.tenant_id == tenant_id,
            Workflow.is_deleted == False,
        )
        if level:
            query = query.filter(Workflow.level == level)
        return query.count()

    def update(self, wf: Workflow) -> Workflow:
        wf.version += 1
        self.db.commit()
        self.db.refresh(wf)
        return wf

    def soft_delete(self, wf: Workflow, deleted_by: str) -> Workflow:
        from datetime import datetime, timezone
        wf.is_deleted = True
        wf.deleted_at = datetime.now(timezone.utc)
        wf.deleted_by = deleted_by
        wf.version += 1
        self.db.commit()
        self.db.refresh(wf)
        return wf

    # ── Steps ─────────────────────────────────

    def add_step(self, step: WorkflowStep) -> WorkflowStep:
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def get_steps(self, workflow_id: str) -> List[WorkflowStep]:
        return self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id,
        ).order_by(WorkflowStep.step_order).all()

    def get_step_by_id(self, step_id: str) -> Optional[WorkflowStep]:
        return self.db.query(WorkflowStep).filter(
            WorkflowStep.id == step_id,
        ).first()

    def update_step(self, step: WorkflowStep) -> WorkflowStep:
        self.db.commit()
        self.db.refresh(step)
        return step

    def delete_step(self, step_id: str) -> None:
        self.db.query(WorkflowStep).filter(
            WorkflowStep.id == step_id,
        ).delete()
        self.db.commit()

    def delete_all_steps(self, workflow_id: str) -> None:
        self.db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow_id,
        ).delete()
        self.db.commit()

    # ── Executions ────────────────────────────

    def create_execution(self, exe: WorkflowExecution) -> WorkflowExecution:
        self.db.add(exe)
        self.db.commit()
        self.db.refresh(exe)
        return exe

    def get_execution(self, exe_id: str) -> Optional[WorkflowExecution]:
        return self.db.query(WorkflowExecution).filter(
            WorkflowExecution.id == exe_id,
        ).first()

    def list_executions(self, workflow_id: str, limit: int = 20) -> List[WorkflowExecution]:
        return self.db.query(WorkflowExecution).filter(
            WorkflowExecution.workflow_id == workflow_id,
        ).order_by(WorkflowExecution.started_at.desc()).limit(limit).all()

    def update_execution(self, exe: WorkflowExecution) -> WorkflowExecution:
        self.db.commit()
        self.db.refresh(exe)
        return exe

    def create_step_execution(self, step_exe: WorkflowStepExecution) -> WorkflowStepExecution:
        self.db.add(step_exe)
        self.db.commit()
        self.db.refresh(step_exe)
        return step_exe

    def update_step_execution(self, step_exe: WorkflowStepExecution) -> WorkflowStepExecution:
        self.db.commit()
        self.db.refresh(step_exe)
        return step_exe

    def get_step_executions(self, execution_id: str) -> List[WorkflowStepExecution]:
        return self.db.query(WorkflowStepExecution).filter(
            WorkflowStepExecution.execution_id == execution_id,
        ).order_by(WorkflowStepExecution.started_at).all()

    # ── Monitoring ────────────────────────────

    def get_monitoring_stats(self, tenant_id: str) -> dict:
        stats = self.db.query(
            func.count(WorkflowExecution.id).label("total"),
            func.count(WorkflowExecution.id).filter(WorkflowExecution.status == "completed").label("completed"),
            func.count(WorkflowExecution.id).filter(WorkflowExecution.status == "failed").label("failed"),
            func.count(WorkflowExecution.id).filter(WorkflowExecution.status == "running").label("running"),
            func.count(WorkflowExecution.id).filter(WorkflowExecution.status == "pending_approval").label("pending"),
            func.avg(WorkflowExecution.duration_ms).label("avg_duration_ms"),
        ).filter(WorkflowExecution.tenant_id == tenant_id).first()

        workflows = self.list_all(tenant_id, skip=0, limit=500)
        active_count = sum(1 for wf in workflows if wf.is_active)

        return {
            "total_executions": stats.total or 0,
            "completed": stats.completed or 0,
            "failed": stats.failed or 0,
            "running": stats.running or 0,
            "pending_approval": stats.pending or 0,
            "avg_duration_ms": round(stats.avg_duration_ms, 1) if stats.avg_duration_ms else 0,
            "success_rate": round((stats.completed / stats.total) * 100, 1) if stats.total else 0,
            "total_workflows": len(workflows),
            "active_workflows": active_count,
        }

    def list_recent_executions(
        self,
        tenant_id: str,
        limit: int = 20,
        status_filter: Optional[str] = None,
    ) -> List[WorkflowExecution]:
        query = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.tenant_id == tenant_id,
        )
        if status_filter:
            query = query.filter(WorkflowExecution.status == status_filter)
        return query.order_by(WorkflowExecution.started_at.desc()).limit(limit).all()
