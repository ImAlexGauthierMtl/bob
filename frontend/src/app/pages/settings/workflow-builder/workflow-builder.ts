import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { UpperCasePipe } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CdkDragDrop, DragDropModule, moveItemInArray } from '@angular/cdk/drag-drop';
import {
    WorkflowService,
    Workflow,
    WorkflowStep,
    WorkflowExecution,
} from '../../../shared/services/workflow.service';

// ── Step type registry ──────────────────────────

interface StepTypeConfig {
    label: string;
    icon: string;
    color: string;
    description: string;
}

const STEP_TYPES: Record<string, StepTypeConfig> = {
    trigger: {
        label: 'Trigger',
        icon: 'fa-solid fa-bolt',
        color: '#3b82f6',
        description: 'Entry point that starts the workflow',
    },
    ai_analysis: {
        label: 'AI Analysis',
        icon: 'fa-solid fa-brain',
        color: '#8b5cf6',
        description: 'Agent analyzes data using LLM',
    },
    condition: {
        label: 'Condition',
        icon: 'fa-solid fa-code-branch',
        color: '#6366f1',
        description: 'Branch based on data values',
    },
    action: {
        label: 'Action',
        icon: 'fa-solid fa-play',
        color: '#10b981',
        description: 'Execute a task or API call',
    },
    human_approval: {
        label: 'Human Approval',
        icon: 'fa-solid fa-user-check',
        color: '#f59e0b',
        description: 'Pause for human review',
    },
    notify: {
        label: 'Notify',
        icon: 'fa-solid fa-bell',
        color: '#ec4899',
        description: 'Send notification or alert',
    },
    log_action: {
        label: 'Log',
        icon: 'fa-solid fa-file-lines',
        color: '#6b7280',
        description: 'Record an audit log entry',
    },
};

// ── Agent node registry ─────────────────────────

const AGENT_NODES: Record<string, string> = {
    ai_analyze: 'AI Analyze — LLM-powered data analysis',
    ai_enrich: 'AI Enrich — Augment data with external sources',
    ai_score: 'AI Score — Calculate scoring via AI',
    log_action: 'Log Action — Write to audit trail',
    notify: 'Notify — Send notification',
    condition_check: 'Condition Check — Evaluate rules',
    update_record: 'Update Record — Modify entity data',
    create_task: 'Create Task — Generate follow-up task',
    webhook_call: 'Webhook Call — HTTP request to external API',
};

@Component({
    selector: 'croo-workflow-builder',
    standalone: true,
    imports: [FormsModule, UpperCasePipe, DragDropModule, RouterLink],
    templateUrl: './workflow-builder.html',
    styleUrls: ['./workflow-builder.css'],
})
export class WorkflowBuilderComponent implements OnInit {
    // ── State ────────────────────────────
    workflow: Workflow | null = null;
    isLoading = true;
    isSaving = false;
    isNewWorkflow = false;
    hasChanges = false;

    // ── Selected step ────────────────────
    selectedStep: WorkflowStep | null = null;
    selectedStepIndex = -1;

    // ── New workflow form ─────────────────
    newWorkflow = {
        name: '',
        description: '',
        level: 'user' as 'system' | 'company' | 'department' | 'user',
        trigger_type: 'manual',
        execution_mode: 'suggest' as 'auto' | 'approval' | 'suggest',
        module: '',
        category: '',
    };

    // ── Palette ──────────────────────────
    stepTypes = STEP_TYPES;
    stepTypeKeys = Object.keys(STEP_TYPES);
    agentNodes = AGENT_NODES;
    agentNodeKeys = Object.keys(AGENT_NODES);

    // ── Execution test ───────────────────
    testRunning = false;
    lastExecution: WorkflowExecution | null = null;

    constructor(
        private workflowService: WorkflowService,
        private route: ActivatedRoute,
        private router: Router,
    ) { }

    ngOnInit(): void {
        const id = this.route.snapshot.paramMap.get('id');
        if (id === 'new') {
            this.isNewWorkflow = true;
            this.isLoading = false;
            this.workflow = null;
        } else if (id) {
            this.loadWorkflow(id);
        }
    }

    loadWorkflow(id: string): void {
        this.isLoading = true;
        this.workflowService.getById(id).subscribe({
            next: (wf) => {
                this.workflow = wf;
                // Sort steps by step_order
                this.workflow.steps = [...wf.steps].sort((a, b) => a.step_order - b.step_order);
                this.isLoading = false;
            },
            error: () => {
                this.isLoading = false;
            },
        });
    }

    // ── Create new workflow ──────────────

    createWorkflow(): void {
        this.isSaving = true;
        this.workflowService.create({
            name: this.newWorkflow.name,
            description: this.newWorkflow.description,
            level: this.newWorkflow.level,
            trigger_type: this.newWorkflow.trigger_type,
            execution_mode: this.newWorkflow.execution_mode,
            module: this.newWorkflow.module || undefined,
            category: this.newWorkflow.category || undefined,
            steps: [{
                name: 'Trigger',
                step_order: 0,
                step_type: 'trigger',
                is_entry_point: true,
                description: 'Workflow entry point',
            }],
        }).subscribe({
            next: (wf) => {
                this.workflow = wf;
                this.workflow.steps = [...wf.steps].sort((a, b) => a.step_order - b.step_order);
                this.isNewWorkflow = false;
                this.isSaving = false;
                // Update URL without reloading
                this.router.navigate(['../', wf.id], { relativeTo: this.route, replaceUrl: true });
            },
            error: () => {
                this.isSaving = false;
            },
        });
    }

    // ── Drag & Drop ─────────────────────

    onStepDrop(event: CdkDragDrop<WorkflowStep[]>): void {
        if (!this.workflow) return;
        moveItemInArray(this.workflow.steps, event.previousIndex, event.currentIndex);
        // Update step_order for all steps
        this.workflow.steps.forEach((step, i) => {
            step.step_order = i;
        });
        this.hasChanges = true;
    }

    // ── Step Selection ──────────────────

    selectStep(step: WorkflowStep, index: number): void {
        this.selectedStep = { ...step }; // clone for editing
        this.selectedStepIndex = index;
    }

    deselectStep(): void {
        this.selectedStep = null;
        this.selectedStepIndex = -1;
    }

    // ── Add Step from Palette ───────────

    addStepFromPalette(type: string): void {
        if (!this.workflow) return;
        const order = this.workflow.steps.length;
        const config = STEP_TYPES[type];

        this.workflowService.addStep(this.workflow.id, {
            name: config.label,
            step_order: order,
            step_type: type as WorkflowStep['step_type'],
            agent_node: null,
            config: null,
            on_success: null,
            on_failure: null,
            description: config.description,
            is_entry_point: false,
        }).subscribe({
            next: (step) => {
                this.workflow!.steps.push(step);
                this.selectStep(step, this.workflow!.steps.length - 1);
            },
        });
    }

    // ── Save Step Config ─────────────────

    saveStepConfig(): void {
        if (!this.workflow || !this.selectedStep) return;
        this.isSaving = true;

        this.workflowService.updateStep(
            this.workflow.id,
            this.selectedStep.id,
            {
                name: this.selectedStep.name,
                step_type: this.selectedStep.step_type,
                agent_node: this.selectedStep.agent_node,
                config: this.selectedStep.config,
                description: this.selectedStep.description,
            }
        ).subscribe({
            next: (updated) => {
                const idx = this.workflow!.steps.findIndex(s => s.id === updated.id);
                if (idx >= 0) this.workflow!.steps[idx] = updated;
                this.isSaving = false;
                this.selectedStep = { ...updated };
            },
            error: () => {
                this.isSaving = false;
            },
        });
    }

    // ── Delete Step ──────────────────────

    deleteStep(step: WorkflowStep): void {
        if (!this.workflow) return;
        this.workflowService.deleteStep(this.workflow.id, step.id).subscribe({
            next: () => {
                this.workflow!.steps = this.workflow!.steps.filter(s => s.id !== step.id);
                if (this.selectedStep?.id === step.id) {
                    this.deselectStep();
                }
            },
        });
    }

    // ── Save Step Order ──────────────────

    saveStepOrder(): void {
        if (!this.workflow) return;
        this.isSaving = true;
        let pendingUpdates = this.workflow.steps.length;

        this.workflow.steps.forEach((step) => {
            this.workflowService.updateStep(this.workflow!.id, step.id, {
                step_order: step.step_order,
            }).subscribe({
                next: () => {
                    pendingUpdates--;
                    if (pendingUpdates === 0) {
                        this.isSaving = false;
                        this.hasChanges = false;
                    }
                },
                error: () => {
                    pendingUpdates--;
                    if (pendingUpdates === 0) {
                        this.isSaving = false;
                    }
                },
            });
        });
    }

    // ── Save Workflow Settings ────────────

    saveWorkflowSettings(): void {
        if (!this.workflow) return;
        this.isSaving = true;
        this.workflowService.update(this.workflow.id, {
            name: this.workflow.name,
            description: this.workflow.description || '',
            execution_mode: this.workflow.execution_mode,
            trigger_type: this.workflow.trigger_type,
        }).subscribe({
            next: (updated) => {
                this.workflow = { ...this.workflow!, ...updated };
                this.isSaving = false;
            },
            error: () => {
                this.isSaving = false;
            },
        });
    }

    // ── Test Run ─────────────────────────

    testRun(): void {
        if (!this.workflow) return;
        this.testRunning = true;
        this.lastExecution = null;

        this.workflowService.run(this.workflow.id, { source: 'builder-test' }).subscribe({
            next: (exe) => {
                this.lastExecution = exe;
                this.testRunning = false;
            },
            error: () => {
                this.testRunning = false;
            },
        });
    }

    // ── Helpers ──────────────────────────

    getStepType(type: string): StepTypeConfig {
        return STEP_TYPES[type] || { label: type, icon: 'fa-solid fa-circle', color: '#6b7280', description: '' };
    }

    isSystemWorkflow(): boolean {
        return this.workflow?.level === 'system';
    }

    getConfigJsonString(): string {
        return this.selectedStep?.config ? JSON.stringify(this.selectedStep.config, null, 2) : '{}';
    }

    setConfigFromJson(jsonStr: string): void {
        if (!this.selectedStep) return;
        try {
            this.selectedStep.config = JSON.parse(jsonStr);
        } catch {
            // Invalid JSON, ignore
        }
    }
}
