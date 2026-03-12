import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TitleCasePipe } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { WorkflowService } from '../../../shared/services/workflow.service';
import { Workflow, WorkflowExecution, UserCapabilities } from '../../../shared/models/workflow.model';

@Component({
    selector: 'croo-settings-automation',
    standalone: true,
    imports: [FormsModule, TitleCasePipe, RouterLink],
    templateUrl: './settings-automation.html',
    styleUrls: ['../settings-shared.css'],
})
export class SettingsAutomationComponent implements OnInit {
    showBanner = true;
    searchQuery = '';
    selectedLevel: 'all' | 'user' | 'company' | 'department' | 'system' = 'all';
    isLoading = true;

    // API data
    workflows: Workflow[] = [];
    templates: Workflow[] = [];
    capabilities: UserCapabilities | null = null;

    // Execution state
    runningWorkflowId: string | null = null;
    lastExecution: WorkflowExecution | null = null;

    private workflowService = inject(WorkflowService);
    private router = inject(Router);

    ngOnInit(): void {
        this.loadWorkflows();
        this.loadTemplates();
        this.loadCapabilities();
    }

    loadWorkflows(): void {
        this.isLoading = true;
        const level = this.selectedLevel === 'all' ? undefined : this.selectedLevel;
        this.workflowService.getAll(level, undefined, false).subscribe({
            next: (res) => {
                this.workflows = res.items;
                this.isLoading = false;
            },
            error: () => {
                this.isLoading = false;
            },
        });
    }

    loadTemplates(): void {
        this.workflowService.getAll(undefined, undefined, true).subscribe({
            next: (res) => {
                this.templates = res.items;
            },
        });
    }

    loadCapabilities(): void {
        this.workflowService.getMyCapabilities().subscribe({
            next: (caps) => {
                this.capabilities = caps;
            },
        });
    }

    // ── Helpers ──────────────────────────

    dismissBanner(): void {
        this.showBanner = false;
    }

    selectLevel(level: 'all' | 'user' | 'company' | 'department' | 'system'): void {
        this.selectedLevel = level;
        this.loadWorkflows();
    }

    toggleAutomation(wf: Workflow): void {
        const newStatus = !wf.is_active;
        this.workflowService.update(wf.id, { is_active: newStatus } as Record<string, unknown>).subscribe({
            next: (updated) => {
                wf.is_active = updated.is_active;
            },
        });
    }

    runWorkflow(wf: Workflow): void {
        this.runningWorkflowId = wf.id;
        this.lastExecution = null;
        this.workflowService.run(wf.id).subscribe({
            next: (exe) => {
                this.lastExecution = exe;
                this.runningWorkflowId = null;
            },
            error: () => {
                this.runningWorkflowId = null;
            },
        });
    }

    useTemplate(tpl: Workflow): void {
        this.workflowService.create({
            name: tpl.name + ' (Copy)',
            description: tpl.description || '',
            level: 'user',
            trigger_type: tpl.trigger_type,
            execution_mode: tpl.execution_mode,
            module: tpl.module || undefined,
            category: tpl.category || undefined,
            steps: tpl.steps.map(s => ({
                name: s.name,
                step_order: s.step_order,
                step_type: s.step_type,
                agent_node: s.agent_node || undefined,
                config: s.config || undefined,
                description: s.description || undefined,
                is_entry_point: s.is_entry_point,
            })),
        }).subscribe({
            next: () => {
                this.loadWorkflows();
            },
        });
    }

    deleteWorkflow(wf: Workflow): void {
        this.workflowService.delete(wf.id).subscribe({
            next: () => {
                this.workflows = this.workflows.filter(w => w.id !== wf.id);
            },
        });
    }

    openBuilder(wf: Workflow): void {
        this.router.navigate(['/settings/automation/builder', wf.id]);
    }

    createNewWorkflow(): void {
        this.router.navigate(['/settings/automation/builder', 'new']);
    }

    get filteredWorkflows(): Workflow[] {
        let result = this.workflows;
        if (this.searchQuery.trim()) {
            const q = this.searchQuery.toLowerCase();
            result = result.filter(w =>
                w.name.toLowerCase().includes(q) || (w.description || '').toLowerCase().includes(q)
            );
        }
        return result;
    }

    getLevelLabel(level: string): string {
        switch (level) {
            case 'user': return 'User Level';
            case 'company': return 'Company Level';
            case 'department': return 'Department Level';
            case 'system': return 'System Level';
            default: return level;
        }
    }

    getLevelBadgeClass(level: string): string {
        switch (level) {
            case 'user': return 'auto-badge--blue';
            case 'company': return 'auto-badge--orange';
            case 'department': return 'auto-badge--indigo';
            case 'system': return 'auto-badge--purple';
            default: return 'auto-badge--gray';
        }
    }

    getStepColor(type: string): string {
        switch (type) {
            case 'trigger': return 'auto-step__num--blue';
            case 'ai_analysis': return 'auto-step__num--purple';
            case 'condition': return 'auto-step__num--indigo';
            case 'action': return 'auto-step__num--green';
            case 'human_approval': return 'auto-step__num--orange';
            default: return 'auto-step__num--gray';
        }
    }

    getStepIcon(type: string): string {
        switch (type) {
            case 'trigger': return 'fa-solid fa-bolt';
            case 'ai_analysis': return 'fa-solid fa-brain';
            case 'condition': return 'fa-solid fa-code-branch';
            case 'action': return 'fa-solid fa-play';
            case 'human_approval': return 'fa-solid fa-user-check';
            default: return 'fa-solid fa-circle';
        }
    }

    getModeIcon(mode: string): string {
        switch (mode) {
            case 'auto': return 'fa-solid fa-robot';
            case 'approval': return 'fa-solid fa-user-shield';
            case 'suggest': return 'fa-solid fa-lightbulb';
            default: return 'fa-solid fa-circle-question';
        }
    }

    getModeLabel(mode: string): string {
        switch (mode) {
            case 'auto': return 'Auto Execute';
            case 'approval': return 'Needs Approval';
            case 'suggest': return 'Suggest Only';
            default: return mode;
        }
    }

    getTemplateIcon(tpl: Workflow): string {
        switch (tpl.category) {
            case 'onboarding': return 'fa-solid fa-handshake';
            case 'lead_management': return 'fa-solid fa-chart-simple';
            case 'notification': return 'fa-solid fa-bell';
            case 'data_sync': return 'fa-solid fa-sync';
            default: return 'fa-solid fa-wand-magic-sparkles';
        }
    }

    formatDate(dateStr: string): string {
        const d = new Date(dateStr);
        const now = new Date();
        const diffDays = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 30) return `${diffDays} days ago`;
        return d.toLocaleDateString();
    }
}
