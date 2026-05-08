// Membrane integration models — mirror backend membrane_schemas

export interface MembraneTokenRequest {
    integration_key: string;
}

export interface MembraneTokenResponse {
    token: string;
    expires_at: string;
}

export interface MembraneConnection {
    id: string;
    integration_id: string;
    integration_key: string;
    name: string;
    disconnected: boolean;
    created_at?: string;
}

export interface MembraneConnectionListResponse {
    items: MembraneConnection[];
}

export interface MembraneIntegration {
    id: string;
    key: string;
    name: string;
    logo_uri?: string;
    description?: string;
}

export interface MembraneIntegrationListResponse {
    items: MembraneIntegration[];
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
    integration_key: string;
}
