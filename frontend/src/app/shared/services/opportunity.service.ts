import { environment } from '../../../environments/environment';
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

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
    created_at: string;
    updated_at: string;
}

export interface OpportunityListResponse {
    items: Opportunity[];
    total: number;
    skip: number;
    limit: number;
}

export interface CreateOpportunityRequest {
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

const API_URL = `${environment.apiUrl}`;

@Injectable({ providedIn: 'root' })
export class OpportunityService {
    constructor(private http: HttpClient) { }

    list(skip = 0, limit = 50, organizationId?: string, stage?: string): Observable<OpportunityListResponse> {
        let url = `${API_URL}/opportunities?skip=${skip}&limit=${limit}`;
        if (organizationId) url += `&organization_id=${organizationId}`;
        if (stage) url += `&stage=${stage}`;
        return this.http.get<OpportunityListResponse>(url);
    }

    getById(id: string): Observable<Opportunity> {
        return this.http.get<Opportunity>(`${API_URL}/opportunities/${id}`);
    }

    create(data: CreateOpportunityRequest): Observable<Opportunity> {
        return this.http.post<Opportunity>(`${API_URL}/opportunities`, data);
    }

    update(id: string, data: Partial<CreateOpportunityRequest>): Observable<Opportunity> {
        return this.http.patch<Opportunity>(`${API_URL}/opportunities/${id}`, data);
    }

    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/opportunities/${id}`);
    }
}
