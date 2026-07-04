// Pipedream integration models. Historical interface names are kept to avoid
// a broad frontend rename while the local email storage is migrated later.

export interface MembraneTokenRequest {
    integration_key: string;
}

export interface MembraneTokenResponse {
    token: string;
    expires_at: string;
    connect_link_url: string;
}

export interface MembraneConnection {
    id: string;
    app?: string;
    integration_id?: string;
    integration_key?: string;
    name: string;
    disconnected?: boolean;
    healthy?: boolean;
    dead?: boolean;
    created_at?: string;
}

export interface MembraneConnectionListResponse {
    items: MembraneConnection[];
}

export interface MembranePageInfo {
    count?: number;
    total_count?: number;
    start_cursor?: string;
    end_cursor?: string;
}

export interface MembraneIntegration {
    id: string;
    key: string;
    name: string;
    logo_uri?: string;
    iconUrl?: string;
    description?: string;
    status?: string;
}

export interface MembraneIntegrationListResponse {
    items: MembraneIntegration[];
    page_info?: MembranePageInfo;
}

export interface MembraneTool {
    key: string;
    name: string;
    description?: string;
    component_type?: string;
    version?: string;
    annotations?: Record<string, unknown>;
    configurable_props_count?: number;
}

export interface MembraneToolListResponse {
    items: MembraneTool[];
    page_info?: MembranePageInfo;
}

export interface MembraneActionRunRequest {
    action_key: string;
    connection_id?: string;
    input: Record<string, unknown>;
}

export interface MembraneActionRunResponse {
    success: boolean;
    output?: Record<string, unknown>;
    error?: string;
}

export interface MembraneConnectUrlResponse {
    url: string;
    app?: string;
    integration_key?: string;
}

export interface MembraneConfig {
    client_id: string;
    /** Optional: leave empty / omit to keep the existing secret unchanged. */
    client_secret?: string;
    project_id: string;
    environment: string;
    api_url: string;
}

export interface MembraneConfigResponse {
    client_id: string;
    project_id: string;
    environment: string;
    api_url: string;
    configured: boolean;
    /** True when a secret is already stored server-side (value never returned). */
    secret_configured: boolean;
    message?: string;
}
