"""Workflow entities — dynamic agent workflow definitions.

A Workflow is a graph of WorkflowSteps, each representing an agent node.
Workflows operate at 4 levels: system | company | department | user.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, JSON

from app.domain.entities.base import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class Workflow(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    """Workflow definition — a graph of agent steps.

    Levels:
    - system: immutable, created by Croo (seeded)
    - company: tenant-wide, created by admin
    - department: scoped to a department
    - user: personal workflow
    """

    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Hierarchy
    level = Column(String(20), nullable=False)  # system | company | department | user
    owner_id = Column(String(36), nullable=True)  # user_id or department_id
    owner_type = Column(String(20), nullable=True)  # user | department

    # Trigger
    trigger_type = Column(String(30), nullable=False, default="manual")  # event | schedule | manual | agent
    trigger_config = Column(JSON, nullable=True)  # event name, cron, etc.

    # Execution
    execution_mode = Column(String(20), nullable=False, default="suggest")  # auto | approval | suggest
    required_capabilities = Column(JSON, nullable=True)  # ["contacts.create", "groq.use"]

    # Override behavior
    is_overridable = Column(Boolean, nullable=False, default=True)
    override_policy = Column(String(20), nullable=False, default="choice")  # choice | cascade | lock
    overrides_workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    is_template = Column(Boolean, nullable=False, default=False)

    # Module association
    module = Column(String(50), nullable=True)  # contacts | organizations | etc.
    category = Column(String(50), nullable=True)  # data_sync | notification | lead_management


class WorkflowStep(Base):
    """A single step (node) in a workflow graph."""

    __tablename__ = "workflow_steps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False, index=True)

    # Step identity
    name = Column(String(150), nullable=False)
    step_order = Column(Integer, nullable=False, default=0)

    # Step type
    step_type = Column(String(30), nullable=False)  # trigger | condition | action | ai_analysis | human_approval
    agent_node = Column(String(100), nullable=True)  # LangGraph node function name

    # Configuration
    config = Column(JSON, nullable=True)  # params for the node

    # Flow control
    on_success = Column(String(36), nullable=True)  # next step_id
    on_failure = Column(String(36), nullable=True)  # fallback step_id or null = end

    # Metadata
    description = Column(Text, nullable=True)
    is_entry_point = Column(Boolean, nullable=False, default=False)
