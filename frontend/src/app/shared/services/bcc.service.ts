import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
    BccOrganization, BccOrgDetail, BccDepartment, BccTeam,
    BccIndustry, BccCareer, BccSkillTemplate, BccTaskTemplate, BccDomain, BccIntent,
    BccRegulation, BccRole, BccRoleDetail,
    BccSkill, BccTask, BccTaskStep, BccResource, BccMilestone,
    BccProfile, BccProfileSection, BccProfileEntry,
    CognitiveMapDomain,
} from '../models/bcc.model';

const API_URL = `${environment.agentControlApiUrl}/bcc`;

@Injectable({ providedIn: 'root' })
export class BccService {
    private http = inject(HttpClient);

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

    // ── Library: Domains ─────────────────────────────────────
    listDomains(): Observable<BccDomain[]> {
        return this.http.get<BccDomain[]>(`${API_URL}/domains`);
    }

    createDomain(data: Partial<BccDomain>): Observable<BccDomain> {
        return this.http.post<BccDomain>(`${API_URL}/domains`, data);
    }

    deleteDomain(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/domains/${id}`);
    }

    // ── Cognitive Map ────────────────────────────────────────
    getCognitiveMap(): Observable<CognitiveMapDomain[]> {
        return this.http.get<CognitiveMapDomain[]>(`${API_URL}/cognitive-map`);
    }

    // ── Library: Intents ─────────────────────────────────────
    listIntents(): Observable<BccIntent[]> {
        return this.http.get<BccIntent[]>(`${API_URL}/intents`);
    }

    getIntent(id: string): Observable<BccIntent> {
        return this.http.get<BccIntent>(`${API_URL}/intents/${id}`);
    }

    createIntent(data: Partial<BccIntent>): Observable<BccIntent> {
        return this.http.post<BccIntent>(`${API_URL}/intents`, data);
    }

    // ── Regulations ──────────────────────────────────────────
    listRegulations(orgId: string): Observable<BccRegulation[]> {
        return this.http.get<BccRegulation[]>(`${API_URL}/organizations/${orgId}/regulations`);
    }

    createRegulation(orgId: string, data: Partial<BccRegulation>): Observable<BccRegulation> {
        return this.http.post<BccRegulation>(`${API_URL}/organizations/${orgId}/regulations`, data);
    }

    // ── Roles ────────────────────────────────────────────────
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

    // ── Skills ───────────────────────────────────────────────
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

    // ── Tasks ────────────────────────────────────────────────
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

    // ── Steps / Resources / Milestones ───────────────────────
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
