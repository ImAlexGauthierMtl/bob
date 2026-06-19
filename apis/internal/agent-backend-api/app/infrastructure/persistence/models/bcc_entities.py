"""Bob's Control Center entities — autonomous knowledge & learning module.

Multi-dimensional architecture:
  Layer 1: Library (reusable templates: Industries, Careers, Skills, Tasks)
  Layer 2: Organization (hierarchy: Org → Department → Team → Role)
  Layer 3: Context Resolution (links + geolocated Regulations)

All tables use 'bcc_' prefix for full isolation from other modules.
"""

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship

from shared.database import Base, TenantMixin, AuditMixin, generate_uuid


# ═══════════════════════════════════════════════════════════════
# LAYER 1 — LIBRARY (reusable templates, not org-specific)
# ═══════════════════════════════════════════════════════════════


class BccIndustry(Base, TenantMixin, AuditMixin):
    """An industry vertical — defines the environment and best practices."""

    __tablename__ = "bcc_industries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    best_practices = Column(JSON, nullable=True, default=dict)

    org_links = relationship("BccOrgIndustry", back_populates="industry", cascade="all, delete-orphan")


class BccCareer(Base, TenantMixin, AuditMixin):
    """A career/profession template — the toolkit for a job."""

    __tablename__ = "bcc_careers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    typical_skills = Column(JSON, nullable=True, default=list)
    typical_tasks = Column(JSON, nullable=True, default=list)

    role_links = relationship("BccRoleCareer", back_populates="career", cascade="all, delete-orphan")


class BccSkillTemplate(Base, TenantMixin, AuditMixin):
    """A reusable skill definition — competency that can be assigned to roles."""

    __tablename__ = "bcc_skill_templates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    type = Column(String(20), nullable=False, default="hard")   # soft | hard | tool
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)

    role_links = relationship("BccRoleSkill", back_populates="skill_template", cascade="all, delete-orphan")


class BccTaskTemplate(Base, TenantMixin, AuditMixin):
    """A reusable task definition — what the user expects to be done."""

    __tablename__ = "bcc_task_templates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    context = Column(JSON, nullable=True, default=dict)
    frequency = Column(String(20), nullable=False, default="ad_hoc")
    category = Column(String(100), nullable=True)
    required_skill_ids = Column(JSON, nullable=True, default=list)

    role_links = relationship("BccRoleTask", back_populates="task_template", cascade="all, delete-orphan")
    intent_links = relationship("BccIntentTask", back_populates="task_template", cascade="all, delete-orphan")


class BccDomain(Base, TenantMixin, AuditMixin):
    """A high-level logical area or module grouping Intents."""

    __tablename__ = "bcc_domains"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)

    intents = relationship("BccIntent", back_populates="domain", cascade="all, delete-orphan", order_by="BccIntent.name")


class BccIntent(Base, TenantMixin, AuditMixin):
    """An intent — what the user wants to achieve. Maps to a sequence of tasks."""

    __tablename__ = "bcc_intents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    trigger_phrases = Column(JSON, nullable=True, default=list)
    category = Column(String(100), nullable=True)
    domain_id = Column(String(36), ForeignKey("bcc_domains.id"), nullable=True)
    workflow_key = Column(String(100), nullable=True)
    pipeline_key = Column(String(100), nullable=True)

    domain = relationship("BccDomain", back_populates="intents")
    task_links = relationship("BccIntentTask", back_populates="intent", cascade="all, delete-orphan",
                              order_by="BccIntentTask.sort_order")


class BccIntentTask(Base, TenantMixin):
    """Junction: Intent ↔ TaskTemplate (ordered, many-to-many)."""

    __tablename__ = "bcc_intent_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    intent_id = Column(String(36), ForeignKey("bcc_intents.id"), nullable=False)
    task_template_id = Column(String(36), ForeignKey("bcc_task_templates.id"), nullable=False)
    sort_order = Column(Integer, default=0)
    tool_name = Column(String(100), nullable=True)

    intent = relationship("BccIntent", back_populates="task_links")
    task_template = relationship("BccTaskTemplate", back_populates="intent_links")

# ═══════════════════════════════════════════════════════════════
# LAYER 2 — ORGANIZATION (hierarchical structure)
# ═══════════════════════════════════════════════════════════════


class BccOrganization(Base, TenantMixin, AuditMixin):
    """Root organizational entity — a company or business unit."""

    __tablename__ = "bcc_organizations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(100), nullable=True)
    color = Column(String(50), nullable=True)

    profile = relationship("BccOrgProfile", back_populates="organization", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    departments = relationship("BccDepartment", back_populates="organization", cascade="all, delete-orphan", lazy="selectin")
    industry_links = relationship("BccOrgIndustry", back_populates="organization", cascade="all, delete-orphan", lazy="selectin")


class BccOrgProfile(Base, TenantMixin, AuditMixin):
    """Organization profile — jurisdiction and operations context."""

    __tablename__ = "bcc_org_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("bcc_organizations.id"), nullable=False, unique=True, index=True)
    country = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    operations_domains = Column(JSON, nullable=True, default=list)

    organization = relationship("BccOrganization", back_populates="profile")
    regulations = relationship("BccRegulation", back_populates="profile", cascade="all, delete-orphan", lazy="selectin")


class BccDepartment(Base, TenantMixin, AuditMixin):
    """A department within an organization."""

    __tablename__ = "bcc_departments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("bcc_organizations.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    organization = relationship("BccOrganization", back_populates="departments")
    teams = relationship("BccTeam", back_populates="department", cascade="all, delete-orphan", lazy="selectin")


class BccTeam(Base, TenantMixin, AuditMixin):
    """A team within a department."""

    __tablename__ = "bcc_teams"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    department_id = Column(String(36), ForeignKey("bcc_departments.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    department = relationship("BccDepartment", back_populates="teams")
    roles = relationship("BccRole", back_populates="team", cascade="all, delete-orphan", lazy="selectin")


class BccRole(Base, TenantMixin, AuditMixin):
    """A job role within a team."""

    __tablename__ = "bcc_roles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    team_id = Column(String(36), ForeignKey("bcc_teams.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    department = Column(String(150), nullable=True)           # legacy field
    description = Column(Text, nullable=True)
    icon = Column(String(100), nullable=True)
    color = Column(String(50), nullable=True)
    kpis = Column(JSON, nullable=True, default=dict)
    context = Column(JSON, nullable=True, default=dict)

    team = relationship("BccTeam", back_populates="roles")

    career_links = relationship("BccRoleCareer", back_populates="role", cascade="all, delete-orphan", lazy="selectin")
    skill_links = relationship("BccRoleSkill", back_populates="role", cascade="all, delete-orphan", lazy="selectin")
    task_links = relationship("BccRoleTask", back_populates="role", cascade="all, delete-orphan", lazy="selectin")

    skills = relationship("BccSkill", back_populates="role", cascade="all, delete-orphan", lazy="selectin")
    tasks = relationship("BccTask", back_populates="role", cascade="all, delete-orphan", lazy="selectin")
    milestones = relationship("BccMilestone", back_populates="role", cascade="all, delete-orphan", lazy="selectin")
    user_roles = relationship("BccUserRole", back_populates="role", cascade="all, delete-orphan", lazy="selectin")


# ═══════════════════════════════════════════════════════════════
# LAYER 3 — CONTEXT RESOLUTION (links + regulations)
# ═══════════════════════════════════════════════════════════════


class BccRegulation(Base, TenantMixin, AuditMixin):
    """A regulatory constraint tied to an org profile/jurisdiction."""

    __tablename__ = "bcc_regulations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    profile_id = Column(String(36), ForeignKey("bcc_org_profiles.id"), nullable=False, index=True)
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=False, default="general")
    scope = Column(String(50), nullable=True)
    enforcement_level = Column(String(20), nullable=False, default="mandatory")
    details = Column(JSON, nullable=True, default=dict)

    profile = relationship("BccOrgProfile", back_populates="regulations")


# ── Association tables ───────────────────────────────────────


class BccOrgIndustry(Base, TenantMixin):
    """Link: Organization ↔ Industry."""

    __tablename__ = "bcc_org_industries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("bcc_organizations.id"), nullable=False, index=True)
    industry_id = Column(String(36), ForeignKey("bcc_industries.id"), nullable=False, index=True)

    organization = relationship("BccOrganization", back_populates="industry_links")
    industry = relationship("BccIndustry", back_populates="org_links")


class BccRoleCareer(Base, TenantMixin):
    """Link: Role ↔ Career."""

    __tablename__ = "bcc_role_careers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    role_id = Column(String(36), ForeignKey("bcc_roles.id"), nullable=False, index=True)
    career_id = Column(String(36), ForeignKey("bcc_careers.id"), nullable=False, index=True)

    role = relationship("BccRole", back_populates="career_links")
    career = relationship("BccCareer", back_populates="role_links")


class BccRoleSkill(Base, TenantMixin):
    """Link: Role ↔ SkillTemplate."""

    __tablename__ = "bcc_role_skills"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    role_id = Column(String(36), ForeignKey("bcc_roles.id"), nullable=False, index=True)
    skill_template_id = Column(String(36), ForeignKey("bcc_skill_templates.id"), nullable=False, index=True)

    role = relationship("BccRole", back_populates="skill_links")
    skill_template = relationship("BccSkillTemplate", back_populates="role_links")


class BccRoleTask(Base, TenantMixin):
    """Link: Role ↔ TaskTemplate."""

    __tablename__ = "bcc_role_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    role_id = Column(String(36), ForeignKey("bcc_roles.id"), nullable=False, index=True)
    task_template_id = Column(String(36), ForeignKey("bcc_task_templates.id"), nullable=False, index=True)

    role = relationship("BccRole", back_populates="task_links")
    task_template = relationship("BccTaskTemplate", back_populates="role_links")


# ═══════════════════════════════════════════════════════════════
# EXISTING ENTITIES (kept for backward compatibility)
# ═══════════════════════════════════════════════════════════════


class BccSkill(Base, TenantMixin, AuditMixin):
    """A competency required for a role — soft, hard, or tool skill."""

    __tablename__ = "bcc_skills"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    role_id = Column(String(36), ForeignKey("bcc_roles.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(20), nullable=False, default="hard")
    stage = Column(String(20), nullable=False, default="foundation")
    priority = Column(Integer, nullable=False, default=3)
    description = Column(Text, nullable=True)
    prerequisites = Column(JSON, nullable=True, default=list)
    training_data = Column(JSON, nullable=True, default=dict)

    role = relationship("BccRole", back_populates="skills")
    resources = relationship("BccResource", back_populates="skill", cascade="all, delete-orphan", lazy="selectin")
    progress = relationship("BccUserProgress", back_populates="skill", cascade="all, delete-orphan")


class BccTask(Base, TenantMixin, AuditMixin):
    """A recurring task that someone in this role performs."""

    __tablename__ = "bcc_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    role_id = Column(String(36), ForeignKey("bcc_roles.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    frequency = Column(String(20), nullable=False, default="daily")
    stage = Column(String(20), nullable=False, default="foundation")
    category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    required_skills = Column(JSON, nullable=True, default=list)
    training_data = Column(JSON, nullable=True, default=dict)

    role = relationship("BccRole", back_populates="tasks")
    steps = relationship("BccTaskStep", back_populates="task", cascade="all, delete-orphan", lazy="selectin",
                         order_by="BccTaskStep.step_number")
    task_logs = relationship("BccUserTaskLog", back_populates="task", cascade="all, delete-orphan")


class BccTaskStep(Base):
    """A single step in a task procedure."""

    __tablename__ = "bcc_task_steps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("bcc_tasks.id"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    instruction = Column(String(500), nullable=False)
    details = Column(Text, nullable=True)

    task = relationship("BccTask", back_populates="steps")


class BccResource(Base, TenantMixin, AuditMixin):
    """A learning resource attached to a skill."""

    __tablename__ = "bcc_resources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    skill_id = Column(String(36), ForeignKey("bcc_skills.id"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    type = Column(String(30), nullable=False, default="article")
    content = Column(Text, nullable=True)
    url = Column(String(500), nullable=True)

    skill = relationship("BccSkill", back_populates="resources")


class BccMilestone(Base, TenantMixin, AuditMixin):
    """A progression marker within a stage."""

    __tablename__ = "bcc_milestones"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    role_id = Column(String(36), ForeignKey("bcc_roles.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    stage = Column(String(20), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    criteria = Column(JSON, nullable=True, default=dict)

    role = relationship("BccRole", back_populates="milestones")


# ── User-level tracking entities ─────────────────────────────


class BccUserRole(Base, TenantMixin, AuditMixin):
    """Assignment of a user to a role with current stage tracking."""

    __tablename__ = "bcc_user_roles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True, comment="Soft ref to user service users.id")
    role_id = Column(String(36), ForeignKey("bcc_roles.id"), nullable=False, index=True)
    current_stage = Column(String(20), nullable=False, default="onboarding")
    assigned_by = Column(String(100), nullable=True)

    role = relationship("BccRole", back_populates="user_roles")


class BccUserProgress(Base, TenantMixin, AuditMixin):
    """Skill progress tracking per user."""

    __tablename__ = "bcc_user_progress"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True, comment="Soft ref to user service users.id")
    skill_id = Column(String(36), ForeignKey("bcc_skills.id"), nullable=False, index=True)
    score = Column(Float, nullable=False, default=0.0)
    source = Column(String(20), nullable=False, default="self")

    skill = relationship("BccSkill", back_populates="progress")


class BccUserTaskLog(Base, TenantMixin, AuditMixin):
    """Log of task completions by a user."""

    __tablename__ = "bcc_user_task_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True, comment="Soft ref to user service users.id")
    task_id = Column(String(36), ForeignKey("bcc_tasks.id"), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    outcome = Column(String(20), nullable=False, default="success")
    notes = Column(Text, nullable=True)

    task = relationship("BccTask", back_populates="task_logs")


# ═══════════════════════════════════════════════════════════════
# LAYER 4 — PROFILE ENTRIES (versioned knowledge management)
# ═══════════════════════════════════════════════════════════════


class BccProfileEntry(Base, TenantMixin, AuditMixin):
    """A versioned knowledge entry for any BCC entity.

    Enables multi-perspective knowledge management:
      - Each entity can have multiple sections
      - Each section can have multiple perspectives (CEO, CFO, Director, Employee)
      - Each perspective is versioned
      - Contributions are tracked
    """

    __tablename__ = "bcc_profile_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(String(36), nullable=False, index=True)

    section = Column(String(100), nullable=False, index=True)
    perspective = Column(String(30), nullable=False, default="general")

    content = Column(Text, nullable=True)
    structured_data = Column(JSON, nullable=True, default=dict)

    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)

    contributed_by = Column(String(36), nullable=True)
    contributor_name = Column(String(200), nullable=True)
    contribution_method = Column(String(20), nullable=False, default="manual")
    conversation_id = Column(String(36), nullable=True)
