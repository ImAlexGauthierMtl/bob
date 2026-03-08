import { environment } from '../../../environments/environment';
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

// ═══════════════════════════════════════════════════════════════
// LAYER 1 — LIBRARY INTERFACES
// ═══════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════
// LAYER 2 — ORGANIZATION INTERFACES
// ═══════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════
// LAYER 3 — CONTEXT / REGULATIONS
// ═══════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════
// EXISTING INTERFACES (backward compat)
// ═══════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════
// SERVICE
// ═══════════════════════════════════════════════════════════════

const API_URL = `${environment.apiUrl}/bcc`;

@Injectable({ providedIn: 'root' })
export class BccService {
    constructor(private http: HttpClient) { }

    // ── Organizations ────────────────────────────────────────
    listOrganizations(): Observable<BccOrganization[]> {
        return this.http.get<BccOrganization[]>(`${API_URL}/organizations`);
    }

    getOrganization(id: string): Observable<BccOrgDetail> {
        return this.http.get<BccOrgDetail>(`${API_URL}/organizations/${id}`);
    }

    createOrganization(data: Partial<BccOrganization>): Observable<BccOrganization> {
        return this.http.post<BccOrganization>(`${API_URL}/organizations`, data);
    }

    deleteOrganization(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/organizations/${id}`);
    }

    // ── Departments ──────────────────────────────────────────
    listDepartments(orgId: string): Observable<BccDepartment[]> {
        return this.http.get<BccDepartment[]>(`${API_URL}/organizations/${orgId}/departments`);
    }

    createDepartment(orgId: string, data: Partial<BccDepartment>): Observable<BccDepartment> {
        return this.http.post<BccDepartment>(`${API_URL}/organizations/${orgId}/departments`, data);
    }

    // ── Teams ────────────────────────────────────────────────
    listTeams(deptId: string): Observable<BccTeam[]> {
        return this.http.get<BccTeam[]>(`${API_URL}/departments/${deptId}/teams`);
    }

    createTeam(deptId: string, data: Partial<BccTeam>): Observable<BccTeam> {
        return this.http.post<BccTeam>(`${API_URL}/departments/${deptId}/teams`, data);
    }

    // ── Team → Roles ─────────────────────────────────────────
    listTeamRoles(teamId: string): Observable<BccRole[]> {
        return this.http.get<BccRole[]>(`${API_URL}/teams/${teamId}/roles`);
    }

    // ── Library: Industries ──────────────────────────────────
    listIndustries(): Observable<BccIndustry[]> {
        return this.http.get<BccIndustry[]>(`${API_URL}/industries`);
    }

    createIndustry(data: Partial<BccIndustry>): Observable<BccIndustry> {
        return this.http.post<BccIndustry>(`${API_URL}/industries`, data);
    }

    getIndustry(id: string): Observable<BccIndustry> {
        return this.http.get<BccIndustry>(`${API_URL}/industries/${id}`);
    }

    // ── Library: Careers ─────────────────────────────────────
    listCareers(): Observable<BccCareer[]> {
        return this.http.get<BccCareer[]>(`${API_URL}/careers`);
    }

    createCareer(data: Partial<BccCareer>): Observable<BccCareer> {
        return this.http.post<BccCareer>(`${API_URL}/careers`, data);
    }

    getCareer(id: string): Observable<BccCareer> {
        return this.http.get<BccCareer>(`${API_URL}/careers/${id}`);
    }

    // ── Library: Skill Templates ─────────────────────────────
    listSkillTemplates(): Observable<BccSkillTemplate[]> {
        return this.http.get<BccSkillTemplate[]>(`${API_URL}/skill-templates`);
    }

    createSkillTemplate(data: Partial<BccSkillTemplate>): Observable<BccSkillTemplate> {
        return this.http.post<BccSkillTemplate>(`${API_URL}/skill-templates`, data);
    }

    getSkillTemplate(id: string): Observable<BccSkillTemplate> {
        return this.http.get<BccSkillTemplate>(`${API_URL}/skill-templates/${id}`);
    }

    // ── Library: Task Templates ──────────────────────────────
    listTaskTemplates(): Observable<BccTaskTemplate[]> {
        return this.http.get<BccTaskTemplate[]>(`${API_URL}/task-templates`);
    }

    createTaskTemplate(data: Partial<BccTaskTemplate>): Observable<BccTaskTemplate> {
        return this.http.post<BccTaskTemplate>(`${API_URL}/task-templates`, data);
    }

    getTaskTemplate(id: string): Observable<BccTaskTemplate> {
        return this.http.get<BccTaskTemplate>(`${API_URL}/task-templates/${id}`);
    }

    // ── Regulations ──────────────────────────────────────────
    listRegulations(orgId: string): Observable<BccRegulation[]> {
        return this.http.get<BccRegulation[]>(`${API_URL}/organizations/${orgId}/regulations`);
    }

    createRegulation(orgId: string, data: Partial<BccRegulation>): Observable<BccRegulation> {
        return this.http.post<BccRegulation>(`${API_URL}/organizations/${orgId}/regulations`, data);
    }

    // ── Existing: Roles ──────────────────────────────────────
    listRoles(): Observable<BccRole[]> {
        return this.http.get<BccRole[]>(`${API_URL}/roles`);
    }

    getRole(id: string): Observable<BccRoleDetail> {
        return this.http.get<BccRoleDetail>(`${API_URL}/roles/${id}`);
    }

    createRole(data: Partial<BccRole>): Observable<BccRole> {
        return this.http.post<BccRole>(`${API_URL}/roles`, data);
    }

    updateRole(id: string, data: Partial<BccRole>): Observable<BccRole> {
        return this.http.put<BccRole>(`${API_URL}/roles/${id}`, data);
    }

    deleteRole(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/roles/${id}`);
    }

    // ── Existing: Skills ─────────────────────────────────────
    getSkill(skillId: string): Observable<BccSkill> {
        return this.http.get<BccSkill>(`${API_URL}/skills/${skillId}`);
    }

    addSkill(roleId: string, data: Partial<BccSkill>): Observable<BccSkill> {
        return this.http.post<BccSkill>(`${API_URL}/roles/${roleId}/skills`, data);
    }

    updateSkill(skillId: string, data: Partial<BccSkill>): Observable<BccSkill> {
        return this.http.put<BccSkill>(`${API_URL}/skills/${skillId}`, data);
    }

    deleteSkill(skillId: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/skills/${skillId}`);
    }

    // ── Existing: Tasks ──────────────────────────────────────
    getTask(taskId: string): Observable<BccTask> {
        return this.http.get<BccTask>(`${API_URL}/tasks/${taskId}`);
    }

    addTask(roleId: string, data: Partial<BccTask>): Observable<BccTask> {
        return this.http.post<BccTask>(`${API_URL}/roles/${roleId}/tasks`, data);
    }

    updateTask(taskId: string, data: Partial<BccTask>): Observable<BccTask> {
        return this.http.put<BccTask>(`${API_URL}/tasks/${taskId}`, data);
    }

    deleteTask(taskId: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/tasks/${taskId}`);
    }

    // ── Existing: Steps / Resources / Milestones ─────────────
    addTaskStep(taskId: string, data: Partial<BccTaskStep>): Observable<BccTaskStep> {
        return this.http.post<BccTaskStep>(`${API_URL}/tasks/${taskId}/steps`, data);
    }

    addResource(skillId: string, data: Partial<BccResource>): Observable<BccResource> {
        return this.http.post<BccResource>(`${API_URL}/skills/${skillId}/resources`, data);
    }

    addMilestone(roleId: string, data: Partial<BccMilestone>): Observable<BccMilestone> {
        return this.http.post<BccMilestone>(`${API_URL}/roles/${roleId}/milestones`, data);
    }

    // ── Profile Entries (versioned knowledge) ────────────────
    getProfile(entityType: string, entityId: string): Observable<BccProfile> {
        return this.http.get<BccProfile>(`${API_URL}/profiles/${entityType}/${entityId}`);
    }

    getProfileSection(entityType: string, entityId: string, section: string): Observable<BccProfileSection> {
        return this.http.get<BccProfileSection>(`${API_URL}/profiles/${entityType}/${entityId}/${section}`);
    }

    getProfileHistory(entityType: string, entityId: string): Observable<BccProfileEntry[]> {
        return this.http.get<BccProfileEntry[]>(`${API_URL}/profiles/${entityType}/${entityId}/history`);
    }

    addProfileEntry(entityType: string, entityId: string, data: Partial<BccProfileEntry>): Observable<BccProfileEntry> {
        return this.http.post<BccProfileEntry>(`${API_URL}/profiles/${entityType}/${entityId}/entries`, data);
    }
}

// ═══════════════════════════════════════════════════════════════
// LAYER 4 — PROFILE ENTRIES (versioned knowledge)
// ═══════════════════════════════════════════════════════════════

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
