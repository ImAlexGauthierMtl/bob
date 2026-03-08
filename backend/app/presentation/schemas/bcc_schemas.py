"""Bob's Control Center schemas — Pydantic request/response models.

Multi-dimensional architecture:
  Layer 1: Library (Industries, Careers, SkillTemplates, TaskTemplates)
  Layer 2: Organization (Org, OrgProfile, Department, Team)
  Layer 3: Context Resolution (Regulations, links)
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ═══════════════════════════════════════════════════════════════
# LAYER 1 — LIBRARY
# ═══════════════════════════════════════════════════════════════


# ── Industry ─────────────────────────────────────────────────

class BccIndustryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    best_practices: Optional[dict] = None


class BccIndustryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    best_practices: Optional[dict] = None


class BccIndustryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    best_practices: Optional[dict] = None

    class Config:
        from_attributes = True


# ── Career ───────────────────────────────────────────────────

class BccCareerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    typical_skills: Optional[list] = None
    typical_tasks: Optional[list] = None


class BccCareerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    typical_skills: Optional[list] = None
    typical_tasks: Optional[list] = None


class BccCareerResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    typical_skills: Optional[list] = None
    typical_tasks: Optional[list] = None

    class Config:
        from_attributes = True


# ── Skill Template ───────────────────────────────────────────

class BccSkillTemplateCreate(BaseModel):
    name: str
    type: str = "hard"
    description: Optional[str] = None
    category: Optional[str] = None


class BccSkillTemplateUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class BccSkillTemplateResponse(BaseModel):
    id: str
    name: str
    type: str
    description: Optional[str] = None
    category: Optional[str] = None

    class Config:
        from_attributes = True


# ── Task Template ────────────────────────────────────────────

class BccTaskTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    context: Optional[dict] = None
    frequency: str = "ad_hoc"
    category: Optional[str] = None
    required_skill_ids: Optional[list] = None


class BccTaskTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    context: Optional[dict] = None
    frequency: Optional[str] = None
    category: Optional[str] = None
    required_skill_ids: Optional[list] = None


class BccTaskTemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    context: Optional[dict] = None
    frequency: str
    category: Optional[str] = None
    required_skill_ids: Optional[list] = None

    class Config:
        from_attributes = True


# ── Intent ───────────────────────────────────────────────────

class BccIntentTaskResponse(BaseModel):
    id: str
    task_template_id: str
    task_template_name: str = ""
    sort_order: int

    class Config:
        from_attributes = True


class BccIntentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_phrases: Optional[list] = None
    category: Optional[str] = None
    task_template_ids: Optional[List[str]] = None


class BccIntentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    trigger_phrases: Optional[list] = None
    category: Optional[str] = None
    task_count: int = 0
    tasks: List[BccIntentTaskResponse] = []

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
# LAYER 2 — ORGANIZATION
# ═══════════════════════════════════════════════════════════════


# ── Organization ─────────────────────────────────────────────

class BccOrganizationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class BccOrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class BccOrgProfileResponse(BaseModel):
    id: str
    country: Optional[str] = None
    state_province: Optional[str] = None
    city: Optional[str] = None
    operations_domains: Optional[list] = None

    class Config:
        from_attributes = True


class BccOrganizationResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    profile: Optional[BccOrgProfileResponse] = None
    department_count: int = 0
    industry_count: int = 0

    class Config:
        from_attributes = True


# ── Organization Profile ─────────────────────────────────────

class BccOrgProfileCreate(BaseModel):
    country: Optional[str] = None
    state_province: Optional[str] = None
    city: Optional[str] = None
    operations_domains: Optional[list] = None


class BccOrgProfileUpdate(BaseModel):
    country: Optional[str] = None
    state_province: Optional[str] = None
    city: Optional[str] = None
    operations_domains: Optional[list] = None


# ── Department ───────────────────────────────────────────────

class BccDepartmentCreate(BaseModel):
    name: str
    description: Optional[str] = None


class BccDepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class BccDepartmentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    organization_id: str
    team_count: int = 0

    class Config:
        from_attributes = True


# ── Team ─────────────────────────────────────────────────────

class BccTeamCreate(BaseModel):
    name: str
    description: Optional[str] = None


class BccTeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class BccTeamResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    department_id: str
    role_count: int = 0

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
# LAYER 3 — CONTEXT / REGULATIONS
# ═══════════════════════════════════════════════════════════════


class BccRegulationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str = "general"               # general | professional | privacy | marketing
    scope: Optional[str] = None         # country | state | city | industry
    enforcement_level: str = "mandatory"  # mandatory | recommended | advisory
    details: Optional[dict] = None


class BccRegulationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    scope: Optional[str] = None
    enforcement_level: Optional[str] = None
    details: Optional[dict] = None


class BccRegulationResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    type: str
    scope: Optional[str] = None
    enforcement_level: str
    details: Optional[dict] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
# EXISTING SCHEMAS (kept for backward compatibility)
# ═══════════════════════════════════════════════════════════════


# ── Role ─────────────────────────────────────────────────────

class BccRoleCreate(BaseModel):
    name: str
    team_id: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    kpis: Optional[dict] = None
    context: Optional[dict] = None


class BccRoleUpdate(BaseModel):
    name: Optional[str] = None
    team_id: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    kpis: Optional[dict] = None
    context: Optional[dict] = None


class BccRoleResponse(BaseModel):
    id: str
    name: str
    team_id: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    kpis: Optional[dict] = None
    context: Optional[dict] = None
    skill_count: int = 0
    task_count: int = 0
    user_count: int = 0

    class Config:
        from_attributes = True


# ── Skill ────────────────────────────────────────────────────

class BccSkillCreate(BaseModel):
    name: str
    type: str = "hard"
    stage: str = "foundation"
    priority: int = 3
    description: Optional[str] = None
    prerequisites: Optional[list] = None
    training_data: Optional[dict] = None


class BccSkillUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    stage: Optional[str] = None
    priority: Optional[int] = None
    description: Optional[str] = None
    prerequisites: Optional[list] = None
    training_data: Optional[dict] = None


class BccResourceResponse(BaseModel):
    id: str
    title: str
    type: str
    content: Optional[str] = None
    url: Optional[str] = None

    class Config:
        from_attributes = True


class BccSkillResponse(BaseModel):
    id: str
    name: str
    type: str
    stage: str
    priority: int
    description: Optional[str] = None
    prerequisites: Optional[list] = None
    training_data: Optional[dict] = None
    resources: List[BccResourceResponse] = []

    class Config:
        from_attributes = True


# ── Task ─────────────────────────────────────────────────────

class BccTaskCreate(BaseModel):
    name: str
    frequency: str = "daily"
    stage: str = "foundation"
    category: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[list] = None
    training_data: Optional[dict] = None


class BccTaskUpdate(BaseModel):
    name: Optional[str] = None
    frequency: Optional[str] = None
    stage: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[list] = None
    training_data: Optional[dict] = None


class BccTaskStepResponse(BaseModel):
    id: str
    step_number: int
    instruction: str
    details: Optional[str] = None

    class Config:
        from_attributes = True


class BccTaskResponse(BaseModel):
    id: str
    name: str
    frequency: str
    stage: str
    category: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[list] = None
    training_data: Optional[dict] = None
    steps: List[BccTaskStepResponse] = []

    class Config:
        from_attributes = True


# ── Task Step ────────────────────────────────────────────────

class BccTaskStepCreate(BaseModel):
    step_number: int
    instruction: str
    details: Optional[str] = None


# ── Resource ─────────────────────────────────────────────────

class BccResourceCreate(BaseModel):
    title: str
    type: str = "article"
    content: Optional[str] = None
    url: Optional[str] = None


# ── Milestone ────────────────────────────────────────────────

class BccMilestoneCreate(BaseModel):
    name: str
    stage: str
    sort_order: int = 0
    criteria: Optional[dict] = None


class BccMilestoneResponse(BaseModel):
    id: str
    name: str
    stage: str
    sort_order: int
    criteria: Optional[dict] = None

    class Config:
        from_attributes = True


# ── Role Detail (combined) ───────────────────────────────────

class BccRoleDetailResponse(BaseModel):
    id: str
    name: str
    team_id: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    kpis: Optional[dict] = None
    context: Optional[dict] = None
    skills: List[BccSkillResponse] = []
    tasks: List[BccTaskResponse] = []
    milestones: List[BccMilestoneResponse] = []
    user_count: int = 0

    class Config:
        from_attributes = True


# ── Organization Detail (combined) ───────────────────────────

class BccOrgDetailResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    profile: Optional[BccOrgProfileResponse] = None
    departments: List[BccDepartmentResponse] = []
    industries: List[BccIndustryResponse] = []
    regulations: List[BccRegulationResponse] = []

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
# LAYER 4 — PROFILE ENTRIES (versioned knowledge)
# ═══════════════════════════════════════════════════════════════


class BccProfileEntryCreate(BaseModel):
    section: str
    content: Optional[str] = None
    structured_data: Optional[dict | list] = None
    perspective: str = "general"
    contribution_method: str = "manual"
    conversation_id: Optional[str] = None


class BccProfileEntryResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    section: str
    content: Optional[str] = None
    structured_data: Optional[dict | list] = None
    perspective: str
    version: int
    is_active: bool
    contributed_by: Optional[str] = None
    contributor_name: Optional[str] = None
    contribution_method: str
    conversation_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BccProfileSectionResponse(BaseModel):
    """Aggregated view — one section with all its active perspectives."""
    section: str
    perspectives: List[BccProfileEntryResponse] = []


class BccProfileResponse(BaseModel):
    """Full profile for an entity — all active sections grouped."""
    entity_type: str
    entity_id: str
    sections: List[BccProfileSectionResponse] = []
