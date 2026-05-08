// Integration Setting model — mirrors backend integration_settings schema

export interface IntegrationSetting {
    id: string;
    integration_key: string;
    scope_mode: 'per-user' | 'per-organization' | 'per-tenant';
    is_enabled: boolean;
    display_name: string | null;
    notes: string | null;
    tenant_id: string;
    created_at: string;
    updated_at: string;
}

export interface IntegrationSettingCreate {
    integration_key: string;
    scope_mode: string;
    is_enabled?: boolean;
    display_name?: string | null;
    notes?: string | null;
}

export interface IntegrationSettingUpdate {
    scope_mode?: string;
    is_enabled?: boolean;
    display_name?: string | null;
    notes?: string | null;
}

export interface IntegrationSettingListResponse {
    items: IntegrationSetting[];
}
