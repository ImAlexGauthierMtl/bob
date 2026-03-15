import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
    Workflow, WorkflowStep, WorkflowListResponse, CreateWorkflowDto,
    WorkflowExecution, ExecutionDetail, UserCapabilities,
} from '../models/workflow.model';

const API_URL = `${environment.platformApiUrl}`;

@Injectable({ providedIn: 'root' })
export class WorkflowService {
    private http = inject(HttpClient);

    // ── Workflows ────────────────────────────

    getAll(level?: string, module?: string, isTemplate?: boolean, skip = 0, limit = 50): Observable<WorkflowListResponse> {
        let url = `${API_URL}/workflows?skip=${skip}&limit=${limit}`;
        if (level) url += `&level=${level}`;
        if (module) url += `&module=${module}`;
        if (isTemplate !== undefined) url += `&is_template=${isTemplate}`;
        return this.http.get<WorkflowListResponse>(url);
    }

    getById(id: string): Observable<Workflow> {
        return this.http.get<Workflow>(`${API_URL}/workflows/${id}`);
    }

    create(data: CreateWorkflowDto): Observable<Workflow> {
        return this.http.post<Workflow>(`${API_URL}/workflows`, data);
    }

    update(id: string, data: Partial<CreateWorkflowDto>): Observable<Workflow> {
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
