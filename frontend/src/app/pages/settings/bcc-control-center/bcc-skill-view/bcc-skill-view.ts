import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { UpperCasePipe, KeyValuePipe } from '@angular/common';
import { BccService } from '../../../../shared/services/bcc.service';
import { BccSkill } from '../../../../shared/models/bcc.model';

@Component({
    selector: 'croo-bcc-skill-view',
    standalone: true,
    imports: [RouterLink, UpperCasePipe, KeyValuePipe],
    templateUrl: './bcc-skill-view.html',
    styleUrls: [
        '../../settings-shared.css',
        '../../../organization-detail/organization-detail.css',
        '../bcc-role-detail/bcc-role-detail.css',
    ],
})
export class BccSkillViewComponent implements OnInit {
    skill: BccSkill | null = null;
    isLoading = true;
    roleId = '';
    orgId = '';

    private bccService = inject(BccService);
    private route = inject(ActivatedRoute);

    ngOnInit(): void {
        this.orgId = this.route.snapshot.paramMap.get('orgId') || '';
        this.roleId = this.route.snapshot.paramMap.get('roleId') || '';
        const skillId = this.route.snapshot.paramMap.get('skillId');
        if (skillId) {
            this.bccService.getSkill(skillId).subscribe({
                next: (data) => { this.skill = data; this.isLoading = false; },
                error: () => { this.isLoading = false; },
            });
        }
    }

    get meta(): Record<string, unknown> {
        return (this.skill?.training_data as Record<string, unknown>) || {};
    }

    get typeLabel(): string {
        switch (this.skill?.type) {
            case 'tool': return 'Tool Skill';
            case 'hard': return 'Hard Skill';
            case 'soft': return 'Soft Skill';
            default: return 'Skill';
        }
    }

    get typeColor(): string {
        switch (this.skill?.type) {
            case 'tool': return '#EF4444';
            case 'hard': return '#F59E0B';
            case 'soft': return '#8B5CF6';
            default: return '#6B7280';
        }
    }

    get typeIcon(): string {
        switch (this.skill?.type) {
            case 'tool': return 'fa-solid fa-wrench';
            case 'hard': return 'fa-solid fa-bolt';
            case 'soft': return 'fa-solid fa-heart';
            default: return 'fa-solid fa-cog';
        }
    }

    get stageLabel(): string {
        const labels: Record<string, string> = {
            'onboarding': '🚀 Onboarding',
            'foundation': '📘 Foundation',
            'practice': '🎯 Practice',
            'mastery': '👑 Mastery',
        };
        return labels[this.skill?.stage || ''] || this.skill?.stage || '';
    }

    getObjectKeys(obj: unknown): string[] {
        return (obj && typeof obj === 'object' && !Array.isArray(obj))
            ? Object.keys(obj as Record<string, unknown>) : [];
    }

    asArray(val: unknown): unknown[] {
        return Array.isArray(val) ? val : [];
    }

    asRecord(val: unknown): Record<string, unknown> {
        return (val !== null && typeof val === 'object' && !Array.isArray(val))
            ? val as Record<string, unknown> : {};
    }

    formatKey(key: string): string {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    getPriorityDots(n: number): number[] {
        return Array(Math.max(0, n)).fill(0);
    }

    getCrmModules(): { module: string; usage: string }[] {
        const raw = this.meta['crm_modules_used'];
        return Array.isArray(raw)
            ? raw as { module: string; usage: string }[]
            : [];
    }

    getCrmModuleIcon(mod: string): string {
        const icons: Record<string, string> = {
            contacts: 'fa-solid fa-address-book',
            organizations: 'fa-solid fa-building',
            opportunities: 'fa-solid fa-chart-line',
            tasks: 'fa-solid fa-list-check',
            analytics: 'fa-solid fa-chart-pie',
            bob_assistant: 'fa-solid fa-robot',
        };
        return icons[mod] || 'fa-solid fa-cube';
    }

    getCrmModuleLabel(mod: string): string {
        const labels: Record<string, string> = {
            contacts: 'Contacts',
            organizations: 'Organizations',
            opportunities: 'Opportunities',
            tasks: 'Tasks & Activities',
            analytics: 'Analytics',
            bob_assistant: 'Bob AI Assistant',
        };
        return labels[mod] || mod;
    }
}
