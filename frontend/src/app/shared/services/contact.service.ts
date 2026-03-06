import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Contact {
    id: string;
    first_name: string;
    last_name: string;
    email: string | null;
    phone: string | null;
    mobile: string | null;
    job_title: string | null;
    department: string | null;
    status: string;
    linkedin_url: string | null;
    notes: string | null;
    organization_id: string | null;
    created_at: string;
    updated_at: string;
}

export interface ContactListResponse {
    items: Contact[];
    total: number;
    skip: number;
    limit: number;
}

export interface CreateContactRequest {
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

const API_URL = 'http://localhost:8555/api/v1';

@Injectable({ providedIn: 'root' })
export class ContactService {
    constructor(private http: HttpClient) { }

    list(skip = 0, limit = 50, organizationId?: string): Observable<ContactListResponse> {
        let url = `${API_URL}/contacts?skip=${skip}&limit=${limit}`;
        if (organizationId) url += `&organization_id=${organizationId}`;
        return this.http.get<ContactListResponse>(url);
    }

    getById(id: string): Observable<Contact> {
        return this.http.get<Contact>(`${API_URL}/contacts/${id}`);
    }

    create(data: CreateContactRequest): Observable<Contact> {
        return this.http.post<Contact>(`${API_URL}/contacts`, data);
    }

    update(id: string, data: Partial<CreateContactRequest>): Observable<Contact> {
        return this.http.patch<Contact>(`${API_URL}/contacts/${id}`, data);
    }

    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/contacts/${id}`);
    }
}
