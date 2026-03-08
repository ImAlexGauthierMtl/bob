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
    organization_id: string | null;
    contact_id: string | null;
    opportunity_id: string | null;
    assigned_to: string | null;
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
    organization_id?: string;
    contact_id?: string;
    opportunity_id?: string;
    assigned_to?: string;
}

export type UpdateActivityDto = Partial<CreateActivityDto>;
