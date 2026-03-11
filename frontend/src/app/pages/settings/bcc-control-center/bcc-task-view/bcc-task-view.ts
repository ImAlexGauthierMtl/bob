import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { UpperCasePipe, KeyValuePipe } from '@angular/common';
import { BccService } from '../../../../shared/services/bcc.service';
import { BccTask } from '../../../../shared/models/bcc.model';

@Component({
    selector: 'croo-bcc-task-view',
    standalone: true,
    imports: [RouterLink, UpperCasePipe],
    templateUrl: './bcc-task-view.html',
    styleUrls: [
        '../../settings-shared.css',
        '../../../organization-detail/organization-detail.css',
        '../bcc-role-detail/bcc-role-detail.css',
    ],
})
export class BccTaskViewComponent implements OnInit {
    task: BccTask | null = null;
    isLoading = true;
    roleId = '';
    orgId = '';

    private bccService = inject(BccService);
    private route = inject(ActivatedRoute);

    ngOnInit(): void {
        this.orgId = this.route.snapshot.paramMap.get('orgId') || '';
        this.roleId = this.route.snapshot.paramMap.get('roleId') || '';
        const taskId = this.route.snapshot.paramMap.get('taskId');
        if (taskId) {
            this.bccService.getTask(taskId).subscribe({
                next: (data) => { this.task = data; this.isLoading = false; },
                error: () => { this.isLoading = false; },
            });
        }
    }

    get meta(): Record<string, unknown> {
        return (this.task?.training_data as Record<string, unknown>) || {};
    }

    get frequencyLabel(): string {
        const labels: Record<string, string> = {
            'daily': '📅 Quotidien',
            'weekly': '📆 Hebdomadaire',
            'monthly': '🗓️ Mensuel',
            'ad_hoc': '⚡ Ad Hoc',
        };
        return labels[this.task?.frequency || ''] || this.task?.frequency || '';
    }

    get frequencyColor(): string {
        const colors: Record<string, string> = {
            'daily': '#EF4444',
            'weekly': '#F59E0B',
            'monthly': '#8B5CF6',
            'ad_hoc': '#6B7280',
        };
        return colors[this.task?.frequency || ''] || '#6B7280';
    }

    get stageLabel(): string {
        const labels: Record<string, string> = {
            'onboarding': '🚀 Onboarding',
            'foundation': '📘 Foundation',
            'practice': '🎯 Practice',
            'mastery': '👑 Mastery',
        };
        return labels[this.task?.stage || ''] || this.task?.stage || '';
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

    getCrmModules(): { module: string; usage: string }[] {
        const raw = this.meta['crm_modules_used'];
        return Array.isArray(raw) ? raw as { module: string; usage: string }[] : [];
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
