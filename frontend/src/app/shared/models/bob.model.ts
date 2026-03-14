// Bob model — mirrors backend Bob Pydantic schemas

export type BobChannel = 'compact' | 'workspace' | 'voice_app' | 'voice_phone';

export interface BobChatRequest {
    message: string;
    session_id?: string;
    mission_prompt?: string;
    mission_context?: Record<string, unknown>;
    channel?: BobChannel;
}

export interface BobChatAction {
    type: string;
    page?: string;
    entity?: string;
    name?: string;
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
