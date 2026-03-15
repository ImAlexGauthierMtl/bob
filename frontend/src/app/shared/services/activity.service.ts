import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Activity, ActivityListResponse, CreateActivityDto } from '../models/activity.model';

const API_URL = `${environment.crmApiUrl}`;

@Injectable({ providedIn: 'root' })
export class ActivityService {
    private http = inject(HttpClient);

    getAll(skip = 0, limit = 50, organizationId?: string, contactId?: string, opportunityId?: string, status?: string): Observable<ActivityListResponse> {
        let url = `${API_URL}/activities?skip=${skip}&limit=${limit}`;
        if (organizationId) url += `&organization_id=${organizationId}`;
        if (contactId) url += `&contact_id=${contactId}`;
        if (opportunityId) url += `&opportunity_id=${opportunityId}`;
        if (status) url += `&activity_status=${status}`;
        return this.http.get<ActivityListResponse>(url);
    }

    getById(id: string): Observable<Activity> {
        return this.http.get<Activity>(`${API_URL}/activities/${id}`);
    }

    create(data: CreateActivityDto): Observable<Activity> {
        return this.http.post<Activity>(`${API_URL}/activities`, data);
    }

    update(id: string, data: Partial<CreateActivityDto>): Observable<Activity> {
        return this.http.patch<Activity>(`${API_URL}/activities/${id}`, data);
    }

    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/activities/${id}`);
    }
}
