// Activity model — mirrors backend ActivityResponse Pydantic schema

export interface Activity {
    id: string;
    subject: string;
    description: string | null;
    activity_type: string;
    priority: string;
    status: string;
    due_date: string | null;
    completed_at: string | null;
    organization_ids: string[];
    contact_ids: string[];
    opportunity_ids: string[];
    assigned_to: string | null;
    owner_id: string | null;
    created_at: string;
    updated_at: string;
}

export interface ActivityListResponse {
    items: Activity[];
    total: number;
    skip: number;
    limit: number;
}

export interface CreateActivityDto {
    subject: string;
    description?: string;
    activity_type?: string;
    priority?: string;
    status?: string;
    due_date?: string;
    organization_ids?: string[];
    contact_ids?: string[];
    opportunity_ids?: string[];
    assigned_to?: string;
    owner_id?: string;
}

export type UpdateActivityDto = Partial<CreateActivityDto>;
