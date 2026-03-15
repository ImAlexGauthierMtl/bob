"""Workflow execution entities — runtime logging.

Tracks every execution of a workflow and each step within it.
"""

from sqlalchemy import Column, String, Text, Integer, Float, ForeignKey, JSON, DateTime, func

from shared.database import Base, TenantMixin, generate_uuid


class WorkflowExecution(Base, TenantMixin):
    """A single execution instance of a workflow."""

    __tablename__ = "workflow_executions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False, index=True)

    # Who triggered it
    triggered_by = Column(String(100), nullable=True)  # user email or "system" or "bob"
    trigger_type = Column(String(30), nullable=True)  # event | schedule | manual | agent

    # Status
    status = Column(String(20), nullable=False, default="running")  # running | completed | failed | cancelled | pending_approval
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Context
    input_data = Column(JSON, nullable=True)  # trigger payload
    output_data = Column(JSON, nullable=True)  # final result
    error = Column(Text, nullable=True)

    # Metrics
    steps_completed = Column(Integer, nullable=False, default=0)
    steps_total = Column(Integer, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=True)


class WorkflowStepExecution(Base):
    """Execution log for a single step within a workflow execution."""

    __tablename__ = "workflow_step_executions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    execution_id = Column(String(36), ForeignKey("workflow_executions.id"), nullable=False, index=True)
    step_id = Column(String(36), ForeignKey("workflow_steps.id"), nullable=False)

    # Status
    status = Column(String(20), nullable=False, default="running")  # running | completed | failed | skipped | pending_approval
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Data
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    # Agent info
    agent_mode_used = Column(String(20), nullable=True)  # auto | approval | suggest
    confidence_score = Column(Float, nullable=True)
    duration_ms = Column(Integer, nullable=True)
