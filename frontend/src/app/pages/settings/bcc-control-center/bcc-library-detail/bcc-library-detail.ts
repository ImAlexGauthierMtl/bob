import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { KeyValuePipe, UpperCasePipe, JsonPipe, DatePipe, LowerCasePipe } from '@angular/common';
import { BccService } from '../../../../shared/services/bcc.service';
import {
    BccIndustry, BccCareer, BccSkillTemplate, BccTaskTemplate, BccIntent,
    BccProfile, BccProfileSection, BccProfileEntry, BccPerspective,
} from '../../../../shared/models/bcc.model';

@Component({
    selector: 'croo-bcc-library-detail',
    standalone: true,
    imports: [RouterLink, KeyValuePipe, UpperCasePipe, JsonPipe, DatePipe, LowerCasePipe],
    templateUrl: './bcc-library-detail.html',
    styleUrls: [
        '../../settings-shared.css',
        '../../../organization-detail/organization-detail.css',
        '../bcc-role-detail/bcc-role-detail.css',
    ],
})
export class BccLibraryDetailComponent implements OnInit {
    type = '';
    item: BccIndustry | BccCareer | BccSkillTemplate | BccTaskTemplate | BccIntent | null = null;
    isLoading = true;

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

    private bccService = inject(BccService);
    private route = inject(ActivatedRoute);

    ngOnInit(): void {
        this.type = this.route.snapshot.paramMap.get('type') || '';
        const id = this.route.snapshot.paramMap.get('id');
        if (id) {
            this.loadItem(id);
        }
    }

    loadItem(id: string): void {
        this.isLoading = true;
        const loaders: Record<string, () => void> = {
            'industry': () => this.bccService.getIndustry(id).subscribe({
                next: (data) => { this.item = data; this.isLoading = false; this.loadProfile(id); },
                error: () => { this.isLoading = false; },
            }),
            'career': () => this.bccService.getCareer(id).subscribe({
                next: (data) => { this.item = data; this.isLoading = false; this.loadProfile(id); },
                error: () => { this.isLoading = false; },
            }),
            'skill-template': () => this.bccService.getSkillTemplate(id).subscribe({
                next: (data) => { this.item = data; this.isLoading = false; this.loadProfile(id); },
                error: () => { this.isLoading = false; },
            }),
            'task-template': () => this.bccService.getTaskTemplate(id).subscribe({
                next: (data) => { this.item = data; this.isLoading = false; this.loadProfile(id); },
                error: () => { this.isLoading = false; },
            }),
            'intent': () => this.bccService.getIntent(id).subscribe({
                next: (data) => { this.item = data; this.isLoading = false; this.loadProfile(id); },
                error: () => { this.isLoading = false; },
            }),
        };
        const loader = loaders[this.type];
        if (loader) loader();
    }

    // ── Profile entry system ─────────────────────────
    get entityType(): string {
        return this.type.replace(/-/g, '_');  // skill-template → skill_template
    }

    loadProfile(entityId: string): void {
        this.bccService.getProfile(this.entityType, entityId).subscribe({
            next: (profile) => { this.profile = profile; },
        });
        this.bccService.getProfileHistory(this.entityType, entityId).subscribe({
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

    // ── Type guards ──────────────────────────────────
    get asIndustry(): BccIndustry | null {
        return this.type === 'industry' ? this.item as BccIndustry : null;
    }
    get asCareer(): BccCareer | null {
        return this.type === 'career' ? this.item as BccCareer : null;
    }
    get asSkillTemplate(): BccSkillTemplate | null {
        return this.type === 'skill-template' ? this.item as BccSkillTemplate : null;
    }
    get asTaskTemplate(): BccTaskTemplate | null {
        return this.type === 'task-template' ? this.item as BccTaskTemplate : null;
    }
    get asIntent(): BccIntent | null {
        return this.type === 'intent' ? this.item as BccIntent : null;
    }

    // ── Helpers ──────────────────────────────────────
    get typeLabel(): string {
        switch (this.type) {
            case 'industry': return 'Industry';
            case 'career': return 'Career';
            case 'skill-template': return 'Skill Template';
            case 'task-template': return 'Task Template';
            case 'intent': return 'Intent';
            default: return 'Library Item';
        }
    }

    get typeIcon(): string {
        switch (this.type) {
            case 'industry': return 'fa-solid fa-industry';
            case 'career': return 'fa-solid fa-briefcase';
            case 'skill-template': return 'fa-solid fa-cog';
            case 'task-template': return 'fa-solid fa-list-check';
            case 'intent': return 'fa-solid fa-bullseye';
            default: return 'fa-solid fa-book';
        }
    }

    get typeColor(): string {
        switch (this.type) {
            case 'industry': return '#8B5CF6';
            case 'career': return '#F59E0B';
            case 'skill-template': return '#EF4444';
            case 'task-template': return '#10B981';
            case 'intent': return '#6366F1';
            default: return '#6B7280';
        }
    }

    getObjectKeys(obj: Record<string, unknown> | null | undefined): string[] {
        return obj ? Object.keys(obj) : [];
    }

    formatKey(key: string): string {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    isArray(val: unknown): boolean {
        return Array.isArray(val);
    }

    isObject(val: unknown): boolean {
        return val !== null && typeof val === 'object' && !Array.isArray(val);
    }

    asArray(val: unknown): unknown[] {
        return Array.isArray(val) ? val : [];
    }

    asRecord(val: unknown): Record<string, unknown> {
        return (val !== null && typeof val === 'object' && !Array.isArray(val))
            ? val as Record<string, unknown> : {};
    }

    asString(val: unknown): string {
        return String(val);
    }

    getSectionIcon(key: string): string {
        const icons: Record<string, string> = {
            'description': 'fa-solid fa-file-lines',
            'vision': 'fa-solid fa-eye',
            'mission': 'fa-solid fa-bullseye',
            'culture': 'fa-solid fa-people-group',
            'competition': 'fa-solid fa-chess',
            'methodology': 'fa-solid fa-diagram-project',
            'stack': 'fa-solid fa-layer-group',
            'decision_making': 'fa-solid fa-chart-line',
            'market_trends': 'fa-solid fa-arrow-trend-up',
            'competitive_landscape': 'fa-solid fa-chess',
            'key_terminology': 'fa-solid fa-book-open',
            'kpis': 'fa-solid fa-gauge-high',
            'regulatory_context': 'fa-solid fa-shield-halved',
            'best_practices': 'fa-solid fa-star',
            'typical_skills': 'fa-solid fa-cog',
            'typical_tasks': 'fa-solid fa-list-check',
            'context': 'fa-solid fa-sitemap',
        };
        return icons[key] || 'fa-solid fa-circle-info';
    }

    getContextIcon(key: string): string {
        const icons: Record<string, string> = {
            'expectations': 'fa-solid fa-bullseye',
            'deliverables': 'fa-solid fa-clipboard-check',
            'success_metrics': 'fa-solid fa-chart-bar',
            'standard_operating_procedure': 'fa-solid fa-list-ol',
            'compliance_requirements': 'fa-solid fa-shield-halved',
            'tools_required': 'fa-solid fa-toolbox',
        };
        return icons[key] || 'fa-solid fa-circle-info';
    }
}
