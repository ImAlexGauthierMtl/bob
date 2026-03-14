export interface SmartLabel {
    id: string;
    name: string;
    color: string;
    description?: string;
    keywords?: string[];
    prompt_hint?: string;
    parent_id?: string | null;
    tenant_id: string;
    created_at: string;
    updated_at: string;
    sub_labels?: SmartLabel[];
    count?: number; // UI only property
}

export interface SmartLabelListResponse {
    items: SmartLabel[];
    total: number;
    skip: number;
    limit: number;
}
