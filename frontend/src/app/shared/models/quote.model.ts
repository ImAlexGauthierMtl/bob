// Quote model — mirrors backend QuoteResponse Pydantic schema

export interface Quote {
    id: string;
    name: string;
    description: string | null;
    status: string;
    subtotal: number | null;
    discount_percent: number | null;
    tax_percent: number | null;
    total: number | null;
    valid_until: string | null;
    terms: string | null;
    notes: string | null;
    opportunity_id: string | null;
    organization_id: string | null;
    created_at: string;
    updated_at: string;
}

export interface QuoteListResponse {
    items: Quote[];
    total: number;
    skip: number;
    limit: number;
}

export interface CreateQuoteDto {
    name: string;
    description?: string;
    status?: string;
    subtotal?: number;
    discount_percent?: number;
    tax_percent?: number;
    total?: number;
    valid_until?: string;
    terms?: string;
    notes?: string;
    opportunity_id?: string;
    organization_id?: string;
}

export type UpdateQuoteDto = Partial<CreateQuoteDto>;
