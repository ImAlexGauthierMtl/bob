import { environment } from '../../../environments/environment';
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Organization {
    id: string;
    name: string;
    industry: string | null;
    website: string | null;
    phone: string | null;
    email: string | null;
    address_street: string | null;
    address_city: string | null;
    address_state: string | null;
    address_country: string | null;
    address_postal_code: string | null;
    status: string;
    org_type: string;
    employee_count: number | null;
    annual_revenue: number | null;
    description: string | null;
    ai_enriched: string;
    linkedin_url: string | null;
    logo_url: string | null;
    organization_profile: OrganizationProfile | null;
    created_at: string;
    updated_at: string;
}

export interface OrganizationProfile {
    company_info?: {
        name?: string;
        legal_name?: string;
        industry?: string;
        sub_industry?: string;
        description?: string;
        founding_year?: number;
        org_type?: string;
        employee_count?: number;
        annual_revenue?: number;
        languages?: string[];
    };
    contact_info?: {
        main_phone?: string;
        other_phones?: string[];
        main_email?: string;
        other_emails?: string[];
        website?: string;
        address?: {
            street?: string;
            city?: string;
            state?: string;
            country?: string;
            postal_code?: string;
        };
    };
    social_media?: {
        linkedin_url?: string;
        facebook_url?: string;
        instagram_url?: string;
        twitter_url?: string;
        youtube_url?: string;
        tiktok_url?: string;
    };
    key_people?: Array<{
        name?: string;
        title?: string;
        email?: string;
        phone?: string;
        linkedin?: string;
    }>;
    services_products?: Array<{
        name?: string;
        description?: string;
        category?: string;
    }>;
    business_details?: {
        target_market?: string;
        geographic_coverage?: string;
        certifications?: string[];
        partners?: string[];
        unique_selling_points?: string[];
    };
}

export interface OrganizationListResponse {
    items: Organization[];
    total: number;
    skip: number;
    limit: number;
}

export interface CreateOrganizationRequest {
    name: string;
    industry?: string;
    website?: string;
    phone?: string;
    address_street?: string;
    address_city?: string;
    address_state?: string;
    address_country?: string;
    address_postal_code?: string;
    status?: string;
}

export interface EnrichmentResult {
    organization_id: string;
    status: string;
    fields_updated: number;
    fields: Record<string, unknown>;
    error: string | null;
}

export interface PlaceResult {
    title: string;
    address: string;
    phone: string | null;
    website: string | null;
    industry: string | null;
    industry_types: string[];
    rating: number | null;
    rating_count: number | null;
    latitude: number | null;
    longitude: number | null;
    thumbnail_url: string | null;
    place_id: string | null;
}

export interface SearchResponse {
    query: string;
    results: PlaceResult[];
    total: number;
}

const API_URL = `${environment.apiUrl}`;

@Injectable({ providedIn: 'root' })
export class OrganizationService {
    constructor(private http: HttpClient) { }

    list(skip = 0, limit = 50): Observable<OrganizationListResponse> {
        return this.http.get<OrganizationListResponse>(`${API_URL}/organizations?skip=${skip}&limit=${limit}`);
    }

    getById(id: string): Observable<Organization> {
        return this.http.get<Organization>(`${API_URL}/organizations/${id}`);
    }

    create(data: CreateOrganizationRequest): Observable<Organization> {
        return this.http.post<Organization>(`${API_URL}/organizations`, data);
    }

    enrich(orgId: string): Observable<EnrichmentResult> {
        return this.http.post<EnrichmentResult>(`${API_URL}/organizations/${orgId}/enrich`, {});
    }

    searchMaps(query: string): Observable<SearchResponse> {
        return this.http.post<SearchResponse>(`${API_URL}/search/maps`, { query });
    }
}
