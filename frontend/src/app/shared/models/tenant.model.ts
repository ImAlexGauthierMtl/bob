// Tenant model — mirrors backend TenantResponse Pydantic schema

export interface Tenant {
    id: string;
    name: string;
    slug: string;
    status: string;
    plan: string;
    owner_email: string;
    owner_name: string;
    max_users: number;
    subscription_start: string | null;
    subscription_end: string | null;
    settings: Record<string, unknown> | null;
    notes: string | null;
    created_at: string;
    updated_at: string;
}

export interface TenantListResponse {
    items: Tenant[];
    total: number;
}

export interface CreateTenantDto {
    name: string;
    slug: string;
    status?: string;
    plan?: string;
    owner_email: string;
    owner_name: string;
    max_users?: number;
    subscription_start?: string;
    subscription_end?: string;
    notes?: string;
}

export type UpdateTenantDto = Partial<CreateTenantDto>;

export interface ProvisionRequest {
    admin_email: string;
    admin_password: string;
    admin_first_name: string;
    admin_last_name: string;
}

export interface ProvisionResponse {
    message: string;
    tenant_id: string;
    admin_user_id: string;
    admin_email: string;
}
