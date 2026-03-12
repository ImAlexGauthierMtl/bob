import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Contact, ContactListResponse, CreateContactDto, AiParseResult } from '../models/contact.model';

const API_URL = `${environment.apiUrl}`;

@Injectable({ providedIn: 'root' })
export class ContactService {
    private http = inject(HttpClient);

    getAll(skip = 0, limit = 50, organizationId?: string): Observable<ContactListResponse> {
        let url = `${API_URL}/contacts?skip=${skip}&limit=${limit}`;
        if (organizationId) url += `&organization_id=${organizationId}`;
        return this.http.get<ContactListResponse>(url);
    }

    getById(id: string): Observable<Contact> {
        return this.http.get<Contact>(`${API_URL}/contacts/${id}`);
    }

    create(data: CreateContactDto): Observable<Contact> {
        return this.http.post<Contact>(`${API_URL}/contacts`, data);
    }

    update(id: string, data: Partial<CreateContactDto>): Observable<Contact> {
        return this.http.patch<Contact>(`${API_URL}/contacts/${id}`, data);
    }

    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/contacts/${id}`);
    }

    aiParse(rawText: string, organizationId?: string): Observable<AiParseResult> {
        return this.http.post<AiParseResult>(`${API_URL}/contacts/ai-parse`, {
            raw_text: rawText,
            organization_id: organizationId ?? null,
        });
    }

    enrichLinkedIn(contactId: string): Observable<any> {
        return this.http.post(`${API_URL}/contacts/${contactId}/enrich-linkedin`, {});
    }
}
