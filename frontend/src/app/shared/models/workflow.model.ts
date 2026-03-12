// Workflow model — mirrors backend WorkflowResponse Pydantic schema

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

export interface CreateWorkflowDto {
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

export type UpdateWorkflowDto = Partial<CreateWorkflowDto>;

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
