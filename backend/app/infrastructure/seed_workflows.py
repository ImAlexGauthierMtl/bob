"""Workflow seed data — system workflows + templates.

Seeds default system-level workflows and template workflows
that users can clone and customize.
"""

import structlog
from sqlalchemy.orm import Session

from app.domain.entities.workflow import Workflow, WorkflowStep

logger = structlog.get_logger(__name__)


SYSTEM_WORKFLOWS = [
    {
        "name": "New Contact Onboarding",
        "description": "Automatically enriches and validates new contacts when they are created",
        "level": "system",
        "trigger_type": "event",
        "trigger_config": {"event": "contact.created"},
        "execution_mode": "auto",
        "required_capabilities": ["contacts.create", "integration.groq"],
        "is_overridable": True,
        "override_policy": "lock",
        "module": "contacts",
        "category": "onboarding",
        "steps": [
            {"name": "Trigger: Contact Created", "step_order": 0, "step_type": "trigger", "is_entry_point": True,
             "description": "Fires when a new contact is added to the system"},
            {"name": "Bob: Validate & Enrich Data", "step_order": 1, "step_type": "ai_analysis",
             "agent_node": "ai_analyze",
             "config": {"prompt": "Validate the contact data and suggest missing fields based on available information."},
             "description": "AI validates data completeness and enriches missing fields"},
            {"name": "Action: Update Contact Record", "step_order": 2, "step_type": "action",
             "agent_node": "log_action",
             "description": "Applies enriched data back to the contact record"},
        ],
    },
    {
        "name": "Organization Enrichment Pipeline",
        "description": "Scrapes website and extracts company information when a new organization is created",
        "level": "system",
        "trigger_type": "event",
        "trigger_config": {"event": "organization.created"},
        "execution_mode": "auto",
        "required_capabilities": ["organizations.create", "integration.groq", "integration.google_maps"],
        "is_overridable": True,
        "override_policy": "lock",
        "module": "organizations",
        "category": "data_sync",
        "steps": [
            {"name": "Trigger: Organization Created", "step_order": 0, "step_type": "trigger", "is_entry_point": True},
            {"name": "Bob: Scrape & Extract", "step_order": 1, "step_type": "ai_analysis",
             "agent_node": "ai_analyze",
             "config": {"prompt": "Extract company information from the organization's website and public sources."}},
            {"name": "Action: Update Organization Profile", "step_order": 2, "step_type": "action",
             "agent_node": "log_action"},
        ],
    },
    {
        "name": "Audit Trail Logger",
        "description": "Records all significant user actions for compliance and security",
        "level": "system",
        "trigger_type": "event",
        "trigger_config": {"event": "*.deleted"},
        "execution_mode": "auto",
        "required_capabilities": [],
        "is_overridable": True,
        "override_policy": "lock",
        "module": None,
        "category": "security",
        "steps": [
            {"name": "Trigger: Destructive Action Detected", "step_order": 0, "step_type": "trigger",
             "is_entry_point": True},
            {"name": "Action: Log to Audit Trail", "step_order": 1, "step_type": "action",
             "agent_node": "log_action", "config": {"log_level": "audit"}},
            {"name": "Notify: Alert Admin", "step_order": 2, "step_type": "action",
             "agent_node": "notify", "config": {"target": "admin", "message": "Destructive action detected"}},
        ],
    },
]


TEMPLATE_WORKFLOWS = [
    {
        "name": "Welcome New Customers",
        "description": "Automatically send onboarding emails, create tasks, and schedule follow-ups for new clients",
        "level": "company",
        "trigger_type": "event",
        "trigger_config": {"event": "organization.created"},
        "execution_mode": "approval",
        "module": "organizations",
        "category": "onboarding",
        "is_template": True,
        "steps": [
            {"name": "Trigger: New Customer Added", "step_order": 0, "step_type": "trigger", "is_entry_point": True},
            {"name": "Bob: Generate Welcome Email", "step_order": 1, "step_type": "ai_analysis",
             "agent_node": "ai_analyze",
             "config": {"prompt": "Draft a personalized welcome email based on the customer's industry and profile."}},
            {"name": "Approval: Review Email", "step_order": 2, "step_type": "human_approval",
             "agent_node": "human_approval"},
            {"name": "Action: Send Email & Create Tasks", "step_order": 3, "step_type": "action",
             "agent_node": "notify", "config": {"target": "customer"}},
        ],
    },
    {
        "name": "Lead Assignment & Distribution",
        "description": "Intelligently assigns new leads to sales reps based on territory, expertise, and current workload",
        "level": "company",
        "trigger_type": "event",
        "trigger_config": {"event": "contact.created"},
        "execution_mode": "auto",
        "module": "contacts",
        "category": "lead_management",
        "is_template": True,
        "steps": [
            {"name": "Trigger: New Lead Created", "step_order": 0, "step_type": "trigger", "is_entry_point": True},
            {"name": "Bob: Analyze Territory & Skills Match", "step_order": 1, "step_type": "ai_analysis",
             "agent_node": "ai_analyze",
             "config": {"prompt": "Match this lead to the best sales rep based on territory, industry expertise, and current capacity."}},
            {"name": "Condition: Check Team Capacity", "step_order": 2, "step_type": "condition",
             "agent_node": "condition",
             "config": {"field": "team_capacity", "operator": "gt", "value": "0"}},
            {"name": "Action: Assign to Rep & Notify", "step_order": 3, "step_type": "action",
             "agent_node": "notify", "config": {"target": "assigned_rep"}},
        ],
    },
    {
        "name": "Pipeline Stage Updates",
        "description": "Notify team members and update records when opportunities move through sales stages",
        "level": "company",
        "trigger_type": "event",
        "trigger_config": {"event": "opportunity.updated"},
        "execution_mode": "auto",
        "module": "opportunities",
        "category": "notification",
        "is_template": True,
        "steps": [
            {"name": "Trigger: Stage Changed", "step_order": 0, "step_type": "trigger", "is_entry_point": True},
            {"name": "Condition: Is Win/Loss?", "step_order": 1, "step_type": "condition",
             "agent_node": "condition",
             "config": {"field": "stage", "operator": "contains", "value": "closed"}},
            {"name": "Action: Notify Team", "step_order": 2, "step_type": "action",
             "agent_node": "notify", "config": {"target": "team", "message": "Opportunity stage updated"}},
        ],
    },
    {
        "name": "Deal Risk Alerts",
        "description": "Bob detects stagnant opportunities and alerts managers to take action",
        "level": "company",
        "trigger_type": "schedule",
        "trigger_config": {"cron": "0 9 * * 1"},
        "execution_mode": "suggest",
        "module": "opportunities",
        "category": "lead_management",
        "is_template": True,
        "steps": [
            {"name": "Trigger: Weekly Monday Check", "step_order": 0, "step_type": "trigger", "is_entry_point": True},
            {"name": "Bob: Analyze Pipeline Health", "step_order": 1, "step_type": "ai_analysis",
             "agent_node": "ai_analyze",
             "config": {"prompt": "Review all open opportunities. Identify deals that have been stagnant for 14+ days or show declining engagement."}},
            {"name": "Action: Alert Managers", "step_order": 2, "step_type": "action",
             "agent_node": "notify", "config": {"target": "manager", "message": "At-risk deals detected"}},
        ],
    },
    {
        "name": "Smart Email Prioritization",
        "description": "Automatically categorizes incoming emails and flags urgent messages requiring immediate attention",
        "level": "user",
        "trigger_type": "event",
        "trigger_config": {"event": "email.received"},
        "execution_mode": "auto",
        "module": None,
        "category": "notification",
        "is_template": True,
        "steps": [
            {"name": "Trigger: New Email Received", "step_order": 0, "step_type": "trigger", "is_entry_point": True},
            {"name": "Bob: Content & Sender Priority", "step_order": 1, "step_type": "ai_analysis",
             "agent_node": "ai_analyze",
             "config": {"prompt": "Analyze this email for urgency, sender importance, and action required. Classify as: urgent, important, normal, or low."}},
            {"name": "Action: Apply Label & Notify", "step_order": 2, "step_type": "action",
             "agent_node": "notify", "config": {"target": "self"}},
        ],
    },
    {
        "name": "Meeting Follow-ups",
        "description": "Create tasks and send summary emails after meetings are completed",
        "level": "user",
        "trigger_type": "event",
        "trigger_config": {"event": "activity.completed"},
        "execution_mode": "approval",
        "module": None,
        "category": "notification",
        "is_template": True,
        "steps": [
            {"name": "Trigger: Meeting Completed", "step_order": 0, "step_type": "trigger", "is_entry_point": True},
            {"name": "Bob: Generate Summary & Action Items", "step_order": 1, "step_type": "ai_analysis",
             "agent_node": "ai_analyze",
             "config": {"prompt": "Generate a meeting summary and extract action items from the meeting notes."}},
            {"name": "Approval: Review Summary", "step_order": 2, "step_type": "human_approval",
             "agent_node": "human_approval"},
            {"name": "Action: Send Summary & Create Tasks", "step_order": 3, "step_type": "action",
             "agent_node": "notify", "config": {"target": "attendees"}},
        ],
    },
]


def seed_workflows(db: Session, tenant_id: str = "default") -> None:
    """Seed system workflows and template workflows."""
    _seed_workflow_list(db, SYSTEM_WORKFLOWS, tenant_id)
    _seed_workflow_list(db, TEMPLATE_WORKFLOWS, tenant_id)


def _seed_workflow_list(db: Session, workflow_defs: list, tenant_id: str) -> None:
    """Seed a list of workflow definitions."""
    seeded = 0
    for wf_data in workflow_defs:
        # Check if already exists
        existing = db.query(Workflow).filter(
            Workflow.name == wf_data["name"],
            Workflow.tenant_id == tenant_id,
            Workflow.is_deleted == False,
        ).first()
        if existing:
            continue

        steps_data = wf_data.pop("steps", [])

        wf = Workflow(
            tenant_id=tenant_id,
            created_by="system-seed",
            is_active=True,
            **wf_data,
        )
        db.add(wf)
        db.flush()  # Get the ID

        for i, step_data in enumerate(steps_data):
            step = WorkflowStep(
                workflow_id=wf.id,
                **step_data,
            )
            db.add(step)

        seeded += 1

    if seeded > 0:
        db.commit()
        logger.info("workflows_seeded", count=seeded, tenant=tenant_id)
    else:
        logger.info("workflows_already_seeded", tenant=tenant_id)
