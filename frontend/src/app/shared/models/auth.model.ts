// Auth model — mirrors backend Auth Pydantic schemas

export interface LoginRequest {
    email: string;
    password: string;
}

export interface RegisterRequest {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
}

export interface AuthSessionUser {
    id: string;
    email?: string;
    display_name?: string;
    first_name?: string;
    last_name?: string;
    status?: string;
}

export interface AuthSessionTenant {
    id: string;
    name?: string;
    status?: string;
    hierarchy_path?: string;
    scope?: string;
}

export interface AuthSession {
    authenticated: boolean;
    session_id?: string;
    user?: AuthSessionUser;
    tenant?: AuthSessionTenant;
    permissions?: string[];
    platform_roles?: string[];
    expires_at?: string;
    source?: string;
}

export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface AuthUser {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    active_organization_id: string | null;
    active_organization_name: string | null;
    role?: string;
    is_super_admin?: boolean;
    created_at: string;
    updated_at: string;
}
