// Bob model — mirrors backend Bob Pydantic schemas

export type BobChannel = 'compact' | 'workspace' | 'voice_app' | 'voice_phone';

export interface BobChatRequest {
    message: string;
    session_id?: string;
    channel?: BobChannel;
    agent_id?: string;
    mission?: {
        id?: string;
        prompt?: string;
        context?: Record<string, unknown>;
    };
    client_context?: Record<string, unknown>;
}

export interface BobChatAction {
    type: string;
    page?: string;
    entity?: string;
    name?: string;
    status?: string;
    content?: string;
    metadata?: Record<string, unknown>;
}

export interface BobArtifactField {
    label: string;
    value: string;
}

export interface BobArtifactLink {
    label: string;
    url: string;
    icon?: string;
}

export interface BobArtifactItem {
    label: string;
    value: string;
    change?: string;       // kpi: "+18%"
    icon?: string;         // info_list: FontAwesome icon class
    percent?: number;      // pipeline/progress: 0-100
    time?: string;         // action_plan: date/time
    description?: string;  // extended description
}

export interface BobArtifactSection {
    title: string;
    subtitle?: string;
    badge?: string;           // e.g. "Priority"
    items: BobArtifactItem[];
}

export interface BobArtifact {
    type: string;
    title: string;
    fields: BobArtifactField[];
    status: 'building' | 'complete' | 'partial';
    entityId?: string;
    links?: BobArtifactLink[];
    // Structured data for new display types
    columns?: string[];
    rows?: string[][];
    items?: BobArtifactItem[];
    sections?: BobArtifactSection[];
}

export interface BobChatResponse {
    response: string;
    session_id: string;
    turn_count: number;
    actions: BobChatAction[];
    tool_steps?: { tool: string; status: string }[];
    artifact?: BobArtifact;
    session_title?: string;
}

export interface BobChatV1Message {
    id: string;
    role: string;
    content: string;
    created_at: string;
    metadata?: Record<string, unknown>;
}

export interface BobChatV1Session {
    id: string;
    title: string;
    channel: string;
    status?: string;
    turn_count: number;
    created_at: string;
    updated_at: string;
}

export interface BobChatV1Run {
    id: string;
    status: string;
    mode?: string;
    trace_id?: string;
}

export interface BobChatV1NarrationStep {
    label: string;
    kind: 'lookup' | 'draft' | 'validate' | 'wait_confirmation' | 'summarize';
    status: string;
    safe_to_show: boolean;
}

export interface BobChatV1Response {
    message: BobChatV1Message;
    input_message?: BobChatV1Message;
    session: BobChatV1Session;
    run: BobChatV1Run;
    actions: BobChatAction[];
    narration_steps: BobChatV1NarrationStep[];
    artifacts: BobArtifact[];
}

export interface BobChatV1SessionList {
    items: BobChatV1Session[];
}

export interface BobChatConfirmationResponse {
    id: string;
    run_id: string;
    status: 'pending' | 'confirmed' | 'cancelled' | string;
    label: string;
    created_at: string;
    resolved_at?: string | null;
}

export interface BobSessionInfo {
    session_id: string;
    user_id: string;
    user_email: string;
    turn_count: number;
    created_at: number;
    last_activity: number;
    message_count: number;
    title?: string;
}
