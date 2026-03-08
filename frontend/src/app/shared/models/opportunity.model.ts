// Opportunity model — mirrors backend OpportunityResponse Pydantic schema

export interface Opportunity {
    id: string;
    name: string;
    description: string | null;
    stage: string;
    priority: string;
    amount: number | null;
    probability: number | null;
    close_date: string | null;
    source: string | null;
    organization_id: string | null;
    contact_id: string | null;
    organization_name: string | null;
    contact_name: string | null;
    created_at: string;
    updated_at: string;
}

export interface OpportunityListResponse {
    items: Opportunity[];
    total: number;
    skip: number;
    limit: number;
}

export interface CreateOpportunityDto {
    name: string;
    description?: string;
    stage?: string;
    priority?: string;
    amount?: number;
    probability?: number;
    close_date?: string;
    source?: string;
    organization_id?: string;
    contact_id?: string;
}

export type UpdateOpportunityDto = Partial<CreateOpportunityDto>;

// ── Opportunity-Product line items ──────────────────

export interface OpportunityProduct {
    id: string;
    opportunity_id: string;
    product_id: string;
    quantity: number;
    unit_price: number;
    discount_percent: number | null;
    notes: string | null;
    product_name: string;
    product_category: string;
    product_sku: string | null;
    created_at: string;
}

export interface AddOpportunityProductDto {
    product_id: string;
    quantity: number;
    discount_percent?: number;
    notes?: string;
}

export interface OpportunityProductListResponse {
    items: OpportunityProduct[];
    total: number;
}
