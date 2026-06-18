"""Workflow entities — dynamic agent workflow definitions.

A Workflow is a graph of WorkflowSteps, each representing an agent node.
Workflows operate at 4 levels: system | company | department | user.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, JSON

from app.infrastructure.persistence.models.base import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class Workflow(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    """Workflow definition — a graph of agent steps."""

    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    level = Column(String(20), nullable=False)
    owner_id = Column(String(36), nullable=True)
    owner_type = Column(String(20), nullable=True)

    trigger_type = Column(String(30), nullable=False, default="manual")
    trigger_config = Column(JSON, nullable=True)

    execution_mode = Column(String(20), nullable=False, default="suggest")
    required_capabilities = Column(JSON, nullable=True)

    is_overridable = Column(Boolean, nullable=False, default=True)
    override_policy = Column(String(20), nullable=False, default="choice")
    overrides_workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    is_template = Column(Boolean, nullable=False, default=False)

    module = Column(String(50), nullable=True)
    category = Column(String(50), nullable=True)


class WorkflowStep(Base):
    """A single step (node) in a workflow graph."""

    __tablename__ = "workflow_steps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False, index=True)

    name = Column(String(150), nullable=False)
    step_order = Column(Integer, nullable=False, default=0)

    step_type = Column(String(30), nullable=False)
    agent_node = Column(String(100), nullable=True)

    config = Column(JSON, nullable=True)

    on_success = Column(String(36), nullable=True)
    on_failure = Column(String(36), nullable=True)

    description = Column(Text, nullable=True)
    is_entry_point = Column(Boolean, nullable=False, default=False)
