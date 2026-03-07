import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { UpperCasePipe, DatePipe, LowerCasePipe } from '@angular/common';
import {
    BccService, BccProfile, BccProfileSection, BccProfileEntry, BccPerspective,
} from '../../../../shared/services/bcc.service';

@Component({
    selector: 'croo-bcc-child-profile',
    standalone: true,
    imports: [RouterLink, UpperCasePipe, DatePipe, LowerCasePipe],
    templateUrl: './bcc-child-profile.html',
    styleUrls: [
        '../../settings-shared.css',
        '../../../organization-detail/organization-detail.css',
        '../bcc-role-detail/bcc-role-detail.css',
    ],
})
export class BccChildProfileComponent implements OnInit {
    entityType = '';
    entityId = '';
    entityName = '';
    parentOrgId = '';
    isLoading = true;

    // Profile entries
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

    private bccService = inject(BccService);
    private route = inject(ActivatedRoute);

    ngOnInit(): void {
        this.parentOrgId = this.route.snapshot.paramMap.get('orgId') || '';

        // Detect entity type from URL
        const url = this.route.snapshot.url.map(s => s.path);
        if (url.includes('departments')) {
            this.entityType = 'department';
            this.entityId = this.route.snapshot.paramMap.get('deptId') || '';
        } else if (url.includes('teams')) {
            this.entityType = 'team';
            this.entityId = this.route.snapshot.paramMap.get('teamId') || '';
        }

        if (this.entityId) {
            this.loadEntity();
            this.loadProfile();
        }
    }

    loadEntity(): void {
        this.isLoading = true;
        if (this.entityType === 'department') {
            // Use the org detail to find the department name
            this.bccService.getOrganization(this.parentOrgId).subscribe({
                next: (org) => {
                    const dept = org.departments.find(d => d.id === this.entityId);
                    this.entityName = dept?.name || 'Department';
                    this.isLoading = false;
                },
                error: () => { this.isLoading = false; },
            });
        } else if (this.entityType === 'team') {
            this.bccService.getOrganization(this.parentOrgId).subscribe({
                next: (org) => {
                    // Need to search all teams
                    for (const dept of org.departments) {
                        this.bccService.listTeams(dept.id).subscribe({
                            next: (teams) => {
                                const team = teams.find(t => t.id === this.entityId);
                                if (team) {
                                    this.entityName = team.name;
                                    this.isLoading = false;
                                }
                            },
                        });
                    }
                },
                error: () => { this.isLoading = false; },
            });
        }
    }

    loadProfile(): void {
        this.bccService.getProfile(this.entityType, this.entityId).subscribe({
            next: (profile) => { this.profile = profile; },
        });
        this.bccService.getProfileHistory(this.entityType, this.entityId).subscribe({
            next: (history) => { this.profileHistory = history; },
        });
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

    get typeLabel(): string {
        return this.entityType === 'department' ? 'Department' : 'Team';
    }

    get typeIcon(): string {
        return this.entityType === 'department' ? 'fa-solid fa-sitemap' : 'fa-solid fa-users';
    }

    get typeColor(): string {
        return this.entityType === 'department' ? '#3B82F6' : '#10B981';
    }

    get backUrl(): string {
        return `/settings/bob-control-center/${this.parentOrgId}`;
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
            general: '#6B7280', ceo: '#8B5CF6', cfo: '#3B82F6',
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
        };
        return icons[key] || 'fa-solid fa-circle-info';
    }

    formatKey(key: string): string {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
}
