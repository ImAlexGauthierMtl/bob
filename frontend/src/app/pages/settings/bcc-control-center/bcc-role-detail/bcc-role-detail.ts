import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { UpperCasePipe, DatePipe, LowerCasePipe } from '@angular/common';
import { BccService } from '../../../../shared/services/bcc.service';
import {
    BccOrgDetail, BccDepartment, BccTeam, BccRole,
    BccIndustry, BccRegulation, BccOrgProfile,
    BccProfile, BccProfileSection, BccProfileEntry, BccPerspective,
} from '../../../../shared/models/bcc.model';
import { BccInterviewComponent } from '../bcc-interview/bcc-interview';

@Component({
    selector: 'croo-bcc-role-detail',
    standalone: true,
    imports: [RouterLink, UpperCasePipe, DatePipe, LowerCasePipe, BccInterviewComponent],
    templateUrl: './bcc-role-detail.html',
    styleUrls: [
        '../../settings-shared.css',
        '../../../organization-detail/organization-detail.css',
        './bcc-role-detail.css',
    ],
})
export class BccRoleDetailComponent implements OnInit {
    org: BccOrgDetail | null = null;
    isLoading = true;
    activeTab = 'profile';

    // Drill-down data
    teams: BccTeam[] = [];
    roles: BccRole[] = [];
    loadingTeams = false;
    loadingRoles = false;

    // ── Profile entries (versioned knowledge) ────────
    profile: BccProfile | null = null;
    profileHistory: BccProfileEntry[] = [];
    selectedPerspective: BccPerspective | 'all' = 'all';
    showHistory = false;

    readonly perspectives: { value: BccPerspective | 'all'; label: string }[] = [
        { value: 'all', label: 'All' },
        { value: 'general', label: 'General' },
        { value: 'ceo', label: 'CEO' },
        { value: 'cfo', label: 'CFO' },
        { value: 'director', label: 'Direction' },
        { value: 'employee', label: 'Employee' },
    ];

    readonly knowledgeTabs = [
        { id: 'vision', label: 'Vision', icon: 'fa-solid fa-eye' },
        { id: 'mission', label: 'Mission', icon: 'fa-solid fa-bullseye' },
        { id: 'culture', label: 'Culture', icon: 'fa-solid fa-people-group' },
        { id: 'competition', label: 'Competition', icon: 'fa-solid fa-chess' },
    ];

    private bccService = inject(BccService);
    private route = inject(ActivatedRoute);

    showInterview = false;

    ngOnInit(): void {
        const orgId = this.route.snapshot.paramMap.get('roleId');
        if (orgId) {
            this.loadOrganization(orgId);
        }
    }

    loadOrganization(id: string): void {
        this.isLoading = true;
        this.bccService.getOrganization(id).subscribe({
            next: (org) => {
                this.org = org;
                this.isLoading = false;
                this.loadAllTeams();
                this.loadProfile(id);
            },
            error: () => { this.isLoading = false; },
        });
    }

    launchCeoInterview(): void {
        if (!this.org) return;
        this.showInterview = true;
    }

    closeInterview(): void {
        this.showInterview = false;
    }

    // ── Profile entries system ───────────────────────
    loadProfile(orgId: string): void {
        this.bccService.getProfile('organization', orgId).subscribe({
            next: (profile) => { this.profile = profile; },
        });
        this.bccService.getProfileHistory('organization', orgId).subscribe({
            next: (history) => { this.profileHistory = history; },
        });
    }

    getEntriesForSection(section: string): BccProfileEntry[] {
        if (!this.profile) return [];
        const sec = this.profile.sections.find(s => s.section === section);
        if (!sec) return [];
        if (this.selectedPerspective === 'all') return sec.perspectives;
        return sec.perspectives.filter(p => p.perspective === this.selectedPerspective);
    }

    hasSectionContent(section: string): boolean {
        return this.getEntriesForSection(section).length > 0;
    }

    get filteredSections(): BccProfileSection[] {
        if (!this.profile) return [];
        if (this.selectedPerspective === 'all') return this.profile.sections;
        return this.profile.sections
            .map(s => ({
                ...s,
                perspectives: s.perspectives.filter(p => p.perspective === this.selectedPerspective),
            }))
            .filter(s => s.perspectives.length > 0);
    }

    selectPerspective(p: BccPerspective | 'all'): void {
        this.selectedPerspective = p;
    }

    toggleHistory(): void {
        this.showHistory = !this.showHistory;
    }

    isKnowledgeTab(): boolean {
        return this.knowledgeTabs.some(t => t.id === this.activeTab) || this.activeTab === 'knowledge';
    }

    getPerspectiveLabel(p: string): string {
        const labels: Record<string, string> = {
            general: 'General', ceo: 'CEO', cfo: 'CFO',
            director: 'Direction', employee: 'Employee',
        };
        return labels[p] || p;
    }

    getPerspectiveColor(p: string): string {
        const colors: Record<string, string> = {
            general: '#6B7280', ceo: '#8B5CF6', cfo: '#686862',
            director: '#F59E0B', employee: '#10B981',
        };
        return colors[p] || '#6B7280';
    }

    getMethodIcon(method: string): string {
        switch (method) {
            case 'conversation': return 'fa-solid fa-comments';
            case 'manual': return 'fa-solid fa-pen';
            case 'import': return 'fa-solid fa-file-import';
            default: return 'fa-solid fa-circle-info';
        }
    }

    getSectionIcon(key: string): string {
        const icons: Record<string, string> = {
            'description': 'fa-solid fa-file-lines',
            'vision': 'fa-solid fa-eye',
            'mission': 'fa-solid fa-bullseye',
            'culture': 'fa-solid fa-people-group',
            'competition': 'fa-solid fa-chess',
            'best_practices': 'fa-solid fa-star',
        };
        return icons[key] || 'fa-solid fa-circle-info';
    }

    formatKey(key: string): string {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    // ── Drill-down ───────────────────────────────────
    loadAllTeams(): void {
        if (!this.org) return;
        this.loadingTeams = true;
        this.teams = [];
        this.roles = [];
        for (const dept of this.org.departments) {
            this.bccService.listTeams(dept.id).subscribe({
                next: (teams) => {
                    for (const t of teams) {
                        this.teams.push(t);
                        this.bccService.listTeamRoles(t.id).subscribe({
                            next: (roles) => {
                                for (const r of roles) {
                                    this.roles.push(r);
                                }
                            },
                        });
                    }
                    this.loadingTeams = false;
                },
            });
        }
    }

    setActiveTab(tab: string): void {
        this.activeTab = tab;
    }

    getTeamsForDepartment(deptId: string): BccTeam[] {
        return this.teams.filter(t => t.department_id === deptId);
    }

    getRolesForTeam(teamId: string): BccRole[] {
        return this.roles.filter(r => r.team_id === teamId);
    }

    getRegulationTypeIcon(type: string): string {
        switch (type) {
            case 'marketing': return 'fa-solid fa-envelope';
            case 'privacy': return 'fa-solid fa-shield-halved';
            case 'professional': return 'fa-solid fa-gavel';
            case 'financial': return 'fa-solid fa-coins';
            default: return 'fa-solid fa-scroll';
        }
    }

    getRegulationTypeColor(type: string): string {
        switch (type) {
            case 'marketing': return '#686862';
            case 'privacy': return '#8B5CF6';
            case 'professional': return '#F59E0B';
            case 'financial': return '#10B981';
            default: return '#6B7280';
        }
    }

    getScopeLabel(scope: string): string {
        switch (scope) {
            case 'country': return '🌍 Country-wide';
            case 'state': return '🏛️ State/Province';
            case 'city': return '🏙️ City-level';
            default: return scope;
        }
    }
}
