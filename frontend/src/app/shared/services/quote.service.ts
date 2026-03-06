import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

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

export interface CreateQuoteRequest {
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

const API_URL = 'http://localhost:8555/api/v1';

@Injectable({ providedIn: 'root' })
export class QuoteService {
    constructor(private http: HttpClient) { }

    list(skip = 0, limit = 50, opportunityId?: string, organizationId?: string): Observable<QuoteListResponse> {
        let url = `${API_URL}/quotes?skip=${skip}&limit=${limit}`;
        if (opportunityId) url += `&opportunity_id=${opportunityId}`;
        if (organizationId) url += `&organization_id=${organizationId}`;
        return this.http.get<QuoteListResponse>(url);
    }

    getById(id: string): Observable<Quote> {
        return this.http.get<Quote>(`${API_URL}/quotes/${id}`);
    }

    create(data: CreateQuoteRequest): Observable<Quote> {
        return this.http.post<Quote>(`${API_URL}/quotes`, data);
    }

    update(id: string, data: Partial<CreateQuoteRequest>): Observable<Quote> {
        return this.http.patch<Quote>(`${API_URL}/quotes/${id}`, data);
    }

    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/quotes/${id}`);
    }
}
