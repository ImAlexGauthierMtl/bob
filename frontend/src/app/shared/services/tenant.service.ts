import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
    Tenant, TenantListResponse, CreateTenantDto, UpdateTenantDto,
    ProvisionRequest, ProvisionResponse,
} from '../models/tenant.model';

const API_URL = `${environment.apiUrl}/admin/tenants`;

@Injectable({ providedIn: 'root' })
export class TenantService {
    private http = inject(HttpClient);

    getAll(skip = 0, limit = 50, search?: string, status?: string): Observable<TenantListResponse> {
        let url = `${API_URL}?skip=${skip}&limit=${limit}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (status) url += `&status=${encodeURIComponent(status)}`;
        return this.http.get<TenantListResponse>(url);
    }

    getById(id: string): Observable<Tenant> {
        return this.http.get<Tenant>(`${API_URL}/${id}`);
    }

    create(data: CreateTenantDto): Observable<Tenant> {
        return this.http.post<Tenant>(API_URL, data);
    }

    update(id: string, data: UpdateTenantDto): Observable<Tenant> {
        return this.http.patch<Tenant>(`${API_URL}/${id}`, data);
    }

    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/${id}`);
    }

    provision(id: string, data: ProvisionRequest): Observable<ProvisionResponse> {
        return this.http.post<ProvisionResponse>(`${API_URL}/${id}/provision`, data);
    }
}
