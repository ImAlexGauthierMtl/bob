import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
    Organization, OrganizationListResponse, CreateOrganizationDto,
    EnrichmentResult, SearchResponse,
} from '../models/organization.model';

const API_URL = `${environment.apiUrl}`;

@Injectable({ providedIn: 'root' })
export class OrganizationService {
    private http = inject(HttpClient);

    getAll(skip = 0, limit = 50): Observable<OrganizationListResponse> {
        return this.http.get<OrganizationListResponse>(`${API_URL}/organizations?skip=${skip}&limit=${limit}`);
    }

    getById(id: string): Observable<Organization> {
        return this.http.get<Organization>(`${API_URL}/organizations/${id}`);
    }

    create(data: CreateOrganizationDto): Observable<Organization> {
        return this.http.post<Organization>(`${API_URL}/organizations`, data);
    }

    enrich(orgId: string): Observable<EnrichmentResult> {
        return this.http.post<EnrichmentResult>(`${API_URL}/organizations/${orgId}/enrich`, {});
    }

    searchMaps(query: string): Observable<SearchResponse> {
        return this.http.post<SearchResponse>(`${API_URL}/search/maps`, { query });
    }
}
