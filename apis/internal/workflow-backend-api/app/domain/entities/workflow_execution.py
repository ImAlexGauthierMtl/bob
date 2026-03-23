"""Workflow execution entities — runtime logging.

Tracks every execution of a workflow and each step within it.
"""

from sqlalchemy import Column, String, Text, Integer, Float, ForeignKey, JSON, DateTime, func

from app.domain.entities.base import Base, TenantMixin, generate_uuid


class WorkflowExecution(Base, TenantMixin):
    """A single execution instance of a workflow."""

    __tablename__ = "workflow_executions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False, index=True)

    triggered_by = Column(String(100), nullable=True)
    trigger_type = Column(String(30), nullable=True)

    status = Column(String(20), nullable=False, default="running")
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    steps_completed = Column(Integer, nullable=False, default=0)
    steps_total = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=True)


class WorkflowStepExecution(Base):
    """Execution log for a single step within a workflow execution."""

    __tablename__ = "workflow_step_executions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    execution_id = Column(String(36), ForeignKey("workflow_executions.id"), nullable=False, index=True)
    step_id = Column(String(36), ForeignKey("workflow_steps.id"), nullable=False)

    status = Column(String(20), nullable=False, default="running")
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    agent_mode_used = Column(String(20), nullable=True)
    confidence_score = Column(Float, nullable=True)
    duration_ms = Column(Integer, nullable=True)
