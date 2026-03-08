import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
    Opportunity, OpportunityListResponse, CreateOpportunityDto,
    OpportunityProduct, OpportunityProductListResponse, AddOpportunityProductDto,
} from '../models/opportunity.model';

const API_URL = `${environment.apiUrl}`;

@Injectable({ providedIn: 'root' })
export class OpportunityService {
    private http = inject(HttpClient);

    getAll(skip = 0, limit = 50, organizationId?: string, stage?: string): Observable<OpportunityListResponse> {
        let url = `${API_URL}/opportunities?skip=${skip}&limit=${limit}`;
        if (organizationId) url += `&organization_id=${organizationId}`;
        if (stage) url += `&stage=${stage}`;
        return this.http.get<OpportunityListResponse>(url);
    }

    getById(id: string): Observable<Opportunity> {
        return this.http.get<Opportunity>(`${API_URL}/opportunities/${id}`);
    }

    create(data: CreateOpportunityDto): Observable<Opportunity> {
        return this.http.post<Opportunity>(`${API_URL}/opportunities`, data);
    }

    update(id: string, data: Partial<CreateOpportunityDto>): Observable<Opportunity> {
        return this.http.patch<Opportunity>(`${API_URL}/opportunities/${id}`, data);
    }

    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/opportunities/${id}`);
    }

    // ── Opportunity-Product ──────────────────

    getProducts(oppId: string): Observable<OpportunityProductListResponse> {
        return this.http.get<OpportunityProductListResponse>(`${API_URL}/opportunities/${oppId}/products`);
    }

    addProduct(oppId: string, data: AddOpportunityProductDto): Observable<OpportunityProduct> {
        return this.http.post<OpportunityProduct>(`${API_URL}/opportunities/${oppId}/products`, data);
    }

    removeProduct(oppId: string, lineId: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/opportunities/${oppId}/products/${lineId}`);
    }
}
