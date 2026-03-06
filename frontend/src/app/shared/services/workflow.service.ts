import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

// ── Interfaces ──────────────────────────────────

export interface WorkflowStep {
    id: string;
    workflow_id: string;
    name: string;
    step_order: number;
    step_type: 'trigger' | 'condition' | 'action' | 'ai_analysis' | 'human_approval';
    agent_node: string | null;
    config: Record<string, unknown> | null;
    on_success: string | null;
    on_failure: string | null;
    description: string | null;
    is_entry_point: boolean;
}

export interface Workflow {
    id: string;
    name: string;
    description: string | null;
    level: 'system' | 'company' | 'department' | 'user';
    owner_id: string | null;
    owner_type: string | null;
    trigger_type: string;
    trigger_config: Record<string, unknown> | null;
    execution_mode: 'auto' | 'approval' | 'suggest';
    required_capabilities: string[] | null;
    is_overridable: boolean;
    override_policy: string;
    overrides_workflow_id: string | null;
    is_active: boolean;
    is_template: boolean;
    module: string | null;
    category: string | null;
    steps: WorkflowStep[];
    created_at: string;
    updated_at: string;
}

export interface WorkflowListResponse {
    items: Workflow[];
    total: number;
    skip: number;
    limit: number;
}

export interface CreateWorkflowRequest {
    name: string;
    description?: string;
    level: string;
    trigger_type?: string;
    trigger_config?: Record<string, unknown>;
    execution_mode?: string;
    required_capabilities?: string[];
    is_overridable?: boolean;
    override_policy?: string;
    module?: string;
    category?: string;
    is_template?: boolean;
    steps?: Partial<WorkflowStep>[];
}

export interface WorkflowExecution {
    id: string;
    workflow_id: string;
    triggered_by: string | null;
    trigger_type: string | null;
    status: string;
    started_at: string;
    completed_at: string | null;
    input_data: Record<string, unknown> | null;
    output_data: Record<string, unknown> | null;
    error: string | null;
    steps_completed: number;
    steps_total: number;
    duration_ms: number | null;
}

export interface ExecutionDetail {
    execution: WorkflowExecution;
    steps: WorkflowStepExecution[];
}

export interface WorkflowStepExecution {
    id: string;
    execution_id: string;
    step_id: string;
    status: string;
    started_at: string;
    completed_at: string | null;
    input_data: Record<string, unknown> | null;
    output_data: Record<string, unknown> | null;
    error: string | null;
    agent_mode_used: string | null;
    confidence_score: number | null;
    duration_ms: number | null;
}

export interface UserCapabilities {
    user_id: string;
    agent_mode: string;
    trust_score: number;
    capabilities: UserCapability[];
}

export interface UserCapability {
    code: string;
    name: string;
    scope: string;
    module: string | null;
    risk_level: string;
    granted: boolean;
    source: string;
}

const API_URL = 'http://localhost:8555/api/v1';

@Injectable({ providedIn: 'root' })
export class WorkflowService {
    constructor(private http: HttpClient) { }

    // ── Workflows ────────────────────────────

    list(level?: string, module?: string, isTemplate?: boolean, skip = 0, limit = 50): Observable<WorkflowListResponse> {
        let url = `${API_URL}/workflows?skip=${skip}&limit=${limit}`;
        if (level) url += `&level=${level}`;
        if (module) url += `&module=${module}`;
        if (isTemplate !== undefined) url += `&is_template=${isTemplate}`;
        return this.http.get<WorkflowListResponse>(url);
    }

    getById(id: string): Observable<Workflow> {
        return this.http.get<Workflow>(`${API_URL}/workflows/${id}`);
    }

    create(data: CreateWorkflowRequest): Observable<Workflow> {
        return this.http.post<Workflow>(`${API_URL}/workflows`, data);
    }

    update(id: string, data: Partial<CreateWorkflowRequest>): Observable<Workflow> {
        return this.http.patch<Workflow>(`${API_URL}/workflows/${id}`, data);
    }

    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/workflows/${id}`);
    }

    // ── Steps ────────────────────────────────

    addStep(workflowId: string, step: Omit<WorkflowStep, 'id' | 'workflow_id'>): Observable<WorkflowStep> {
        return this.http.post<WorkflowStep>(`${API_URL}/workflows/${workflowId}/steps`, step);
    }

    updateStep(workflowId: string, stepId: string, data: Partial<WorkflowStep>): Observable<WorkflowStep> {
        return this.http.patch<WorkflowStep>(`${API_URL}/workflows/${workflowId}/steps/${stepId}`, data);
    }

    deleteStep(workflowId: string, stepId: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/workflows/${workflowId}/steps/${stepId}`);
    }

    // ── Execution ────────────────────────────

    run(workflowId: string, inputData?: Record<string, unknown>): Observable<WorkflowExecution> {
        return this.http.post<WorkflowExecution>(`${API_URL}/workflows/${workflowId}/run`, { input_data: inputData });
    }

    listExecutions(workflowId: string, limit = 20): Observable<WorkflowExecution[]> {
        return this.http.get<WorkflowExecution[]>(`${API_URL}/workflows/${workflowId}/executions?limit=${limit}`);
    }

    getExecution(workflowId: string, executionId: string): Observable<ExecutionDetail> {
        return this.http.get<ExecutionDetail>(`${API_URL}/workflows/${workflowId}/executions/${executionId}`);
    }

    // ── Capabilities ─────────────────────────

    getMyCapabilities(): Observable<UserCapabilities> {
        return this.http.get<UserCapabilities>(`${API_URL}/capabilities/me`);
    }
}
