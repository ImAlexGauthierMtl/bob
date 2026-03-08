// Bob model — mirrors backend Bob Pydantic schemas

export interface BobChatRequest {
    message: string;
    session_id?: string;
    mission_prompt?: string;
    mission_context?: Record<string, unknown>;
}

export interface BobChatAction {
    type: string;
    page?: string;
    entity?: string;
    name?: string;
}

export interface BobChatResponse {
    response: string;
    session_id: string;
    turn_count: number;
    actions: BobChatAction[];
    tool_steps?: { tool: string; status: string }[];
}

export interface BobSessionInfo {
    session_id: string;
    user_id: string;
    user_email: string;
    turn_count: number;
    created_at: number;
    last_activity: number;
    message_count: number;
}
