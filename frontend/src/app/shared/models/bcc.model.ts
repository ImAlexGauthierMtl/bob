// BCC (Bob Control Center) model — mirrors backend BCC Pydantic schemas

// ── Layer 1: Library ────────────────────────────────────────────

export interface BccIndustry {
    id: string;
    name: string;
    description: string | null;
    best_practices: Record<string, unknown> | null;
}

export interface BccCareer {
    id: string;
    name: string;
    description: string | null;
    typical_skills: string[] | null;
    typical_tasks: string[] | null;
}

export interface BccSkillTemplate {
    id: string;
    name: string;
    type: string;
    description: string | null;
    category: string | null;
}

export interface BccTaskTemplate {
    id: string;
    name: string;
    description: string | null;
    context: Record<string, unknown> | null;
    frequency: string;
    category: string | null;
    required_skill_ids: string[] | null;
}

export interface BccIntentTask {
    id: string;
    task_template_id: string;
    task_template_name: string;
    sort_order: number;
}

export interface BccIntent {
    id: string;
    name: string;
    description: string | null;
    trigger_phrases: string[] | null;
    category: string | null;
    task_count: number;
    tasks: BccIntentTask[];
}

// ── Layer 2: Organization ───────────────────────────────────────

export interface BccOrgProfile {
    id: string;
    country: string | null;
    state_province: string | null;
    city: string | null;
    operations_domains: string[] | null;
}

export interface BccOrganization {
    id: string;
    name: string;
    description: string | null;
    icon: string | null;
    color: string | null;
    profile: BccOrgProfile | null;
    department_count: number;
    industry_count: number;
}

export interface BccDepartment {
    id: string;
    name: string;
    description: string | null;
    organization_id: string;
    team_count: number;
}

export interface BccTeam {
    id: string;
    name: string;
    description: string | null;
    department_id: string;
    role_count: number;
}

// ── Layer 3: Context / Regulations ──────────────────────────────

export interface BccRegulation {
    id: string;
    name: string;
    description: string | null;
    type: string;
    scope: string | null;
    enforcement_level: string;
    details: Record<string, unknown> | null;
}

export interface BccOrgDetail {
    id: string;
    name: string;
    description: string | null;
    icon: string | null;
    color: string | null;
    profile: BccOrgProfile | null;
    departments: BccDepartment[];
    industries: BccIndustry[];
    regulations: BccRegulation[];
}

// ── Roles / Skills / Tasks ──────────────────────────────────────

export interface BccResource {
    id: string;
    title: string;
    type: string;
    content: string | null;
    url: string | null;
}

export interface BccSkill {
    id: string;
    name: string;
    type: string;
    stage: string;
    priority: number;
    description: string | null;
    prerequisites: string[] | null;
    training_data: Record<string, unknown> | null;
    resources: BccResource[];
}

export interface BccTaskStep {
    id: string;
    step_number: number;
    instruction: string;
    details: string | null;
}

export interface BccTask {
    id: string;
    name: string;
    frequency: string;
    stage: string;
    category: string | null;
    description: string | null;
    required_skills: string[] | null;
    training_data: Record<string, unknown> | null;
    steps: BccTaskStep[];
}

export interface BccMilestone {
    id: string;
    name: string;
    stage: string;
    sort_order: number;
    criteria: Record<string, unknown> | null;
}

export interface BccRole {
    id: string;
    name: string;
    team_id: string | null;
    department: string | null;
    description: string | null;
    icon: string | null;
    color: string | null;
    kpis: Record<string, unknown> | null;
    context: Record<string, unknown> | null;
    skill_count: number;
    task_count: number;
    user_count: number;
}

export interface BccRoleDetail extends BccRole {
    skills: BccSkill[];
    tasks: BccTask[];
    milestones: BccMilestone[];
}

// ── Layer 4: Profile Entries ────────────────────────────────────

export type BccPerspective = 'general' | 'ceo' | 'cfo' | 'director' | 'employee';
export type BccEntityType = 'industry' | 'career' | 'skill_template' | 'task_template'
    | 'organization' | 'department' | 'team' | 'role' | 'regulation';

export interface BccProfileEntry {
    id: string;
    entity_type: BccEntityType;
    entity_id: string;
    section: string;
    content: string | null;
    structured_data: Record<string, unknown> | unknown[] | null;
    perspective: BccPerspective;
    version: number;
    is_active: boolean;
    contributed_by: string | null;
    contributor_name: string | null;
    contribution_method: 'conversation' | 'manual' | 'import';
    conversation_id: string | null;
    created_at: string | null;
}

export interface BccProfileSection {
    section: string;
    perspectives: BccProfileEntry[];
}

export interface BccProfile {
    entity_type: BccEntityType;
    entity_id: string;
    sections: BccProfileSection[];
}
