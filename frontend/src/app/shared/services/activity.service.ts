import { environment } from '../../../environments/environment';
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Activity {
    id: string;
    subject: string;
    description: string | null;
    activity_type: string;
    priority: string;
    status: string;
    due_date: string | null;
    completed_at: string | null;
    organization_id: string | null;
    contact_id: string | null;
    opportunity_id: string | null;
    assigned_to: string | null;
    created_at: string;
    updated_at: string;
}

export interface ActivityListResponse {
    items: Activity[];
    total: number;
    skip: number;
    limit: number;
}

export interface CreateActivityRequest {
    subject: string;
    description?: string;
    activity_type?: string;
    priority?: string;
    status?: string;
    due_date?: string;
    organization_id?: string;
    contact_id?: string;
    opportunity_id?: string;
    assigned_to?: string;
}

const API_URL = `${environment.apiUrl}`;

@Injectable({ providedIn: 'root' })
export class ActivityService {
    constructor(private http: HttpClient) { }

    list(skip = 0, limit = 50, organizationId?: string, contactId?: string, status?: string): Observable<ActivityListResponse> {
        let url = `${API_URL}/activities?skip=${skip}&limit=${limit}`;
        if (organizationId) url += `&organization_id=${organizationId}`;
        if (contactId) url += `&contact_id=${contactId}`;
        if (status) url += `&activity_status=${status}`;
        return this.http.get<ActivityListResponse>(url);
    }

    getById(id: string): Observable<Activity> {
        return this.http.get<Activity>(`${API_URL}/activities/${id}`);
    }

    create(data: CreateActivityRequest): Observable<Activity> {
        return this.http.post<Activity>(`${API_URL}/activities`, data);
    }

    update(id: string, data: Partial<CreateActivityRequest>): Observable<Activity> {
        return this.http.patch<Activity>(`${API_URL}/activities/${id}`, data);
    }

    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/activities/${id}`);
    }
}
