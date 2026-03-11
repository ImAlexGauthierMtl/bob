// Contact model — mirrors backend ContactResponse Pydantic schema

export interface Contact {
    id: string;
    first_name: string;
    last_name: string;
    email: string | null;
    phone: string | null;
    mobile: string | null;
    job_title: string | null;
    department: string | null;
    seniority: string | null;
    status: string;
    linkedin_url: string | null;
    notes: string | null;
    organization_id: string | null;
    contact_profile: ContactProfile | null;
    headline: string | null;
    profile_picture_url: string | null;
    linkedin_followers: any[] | null;
    created_at: string;
    updated_at: string;
}

export interface ContactProfile {
    source?: string;
    confidence?: number;
    seniority?: string;
    department?: string;
    linkedin?: string;
    phone?: string;
    position_raw?: string;
    verification_status?: string;
    verification?: Record<string, unknown>;
    sources?: Array<Record<string, unknown>>;
    last_enriched?: string;
}

export interface ContactListResponse {
    items: Contact[];
    total: number;
    skip: number;
    limit: number;
}

export interface CreateContactDto {
    first_name: string;
    last_name: string;
    email?: string;
    phone?: string;
    mobile?: string;
    job_title?: string;
    department?: string;
    status?: string;
    linkedin_url?: string;
    notes?: string;
    organization_id?: string;
}

export type UpdateContactDto = Partial<CreateContactDto>;

export interface AiParseResult {
    extracted: Partial<CreateContactDto>;
    confidence: number;
    raw_text: string;
}
