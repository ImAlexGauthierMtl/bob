export interface ToolGovernancePolicy {
    id: string;
    display_name: string;
    provider: string;
    integration_key: string | null;
    tool_key: string | null;
    family: string | null;
    capability: string | null;
    risk: string;
    enabled: boolean;
    team_scope: string[];
    sync_enabled: boolean;
    sync_mode: 'none' | 'read_only' | 'import' | 'two_way';
    data_mapping: Record<string, unknown>;
    notes: string | null;
    source: string;
}

export interface ToolGovernancePolicyListResponse {
    source: string;
    scope: string;
    tenant_id: string;
    items: ToolGovernancePolicy[];
    total: number;
    enabled_total: number;
}

export interface UserToolPreferences {
    preferred_email_provider: 'auto' | 'gmail' | 'microsoft_outlook' | 'ask';
    preferred_calendar_provider: 'auto' | 'google_calendar' | 'microsoft_outlook' | 'ask';
    require_write_confirmation: boolean;
    show_tool_trace: boolean;
    allow_personal_connectors: boolean;
}

export interface UserToolAccessResponse {
    source: string;
    scope: string;
    tenant_id: string;
    user_id: string;
    preferences: UserToolPreferences;
    policies?: ToolGovernancePolicy[];
    allowed_tools: ToolGovernancePolicy[];
    allowed_total: number;
}

export type ToolGovernancePolicyUpdate = Partial<Omit<ToolGovernancePolicy, 'id' | 'source'>>;
export type UserToolPreferencesUpdate = Partial<UserToolPreferences>;
