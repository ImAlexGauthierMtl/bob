import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

const API_URL = `${environment.communicationApiUrl}`;

export interface MembraneBackendConnection {
    id: string;
    user_id: string;
    membrane_connection_id: string;
    integration_key: string;
    connection_name: string;
    is_active: boolean;
    last_email_sync: string | null;
    last_calendar_sync: string | null;
    tenant_id: string;
    created_at: string;
}

export interface MembraneBackendEmail {
    id: string;
    membrane_connection_id: string;
    user_id: string;
    provider_message_id: string;
    provider: string;
    subject: string | null;
    body_preview: string | null;
    body_html: string | null;
    from_address: string | null;
    from_name: string | null;
    to_addresses: Array<{ address: string; name: string }> | null;
    cc_addresses: Array<{ address: string; name: string }> | null;
    received_at: string | null;
    is_read: boolean;
    has_attachments: boolean;
    folder: string;
    conversation_id: string | null;
    linked_contact_id: string | null;
    linked_organization_id: string | null;
    tenant_id: string;
    created_at: string;
}

export interface MembraneBackendEvent {
    id: string;
    membrane_connection_id: string;
    user_id: string;
    provider_event_id: string;
    provider: string;
    subject: string | null;
    body_html: string | null;
    location: string | null;
    start_time: string | null;
    end_time: string | null;
    is_all_day: boolean;
    organizer_email: string | null;
    organizer_name: string | null;
    attendees: Array<{ email: string; name: string; status: string }> | null;
    status: string;
    is_cancelled: boolean;
    online_meeting_url: string | null;
    linked_contact_id: string | null;
    linked_organization_id: string | null;
    tenant_id: string;
    created_at: string;
}

export interface MembraneBackendEmailList {
    items: MembraneBackendEmail[];
    total: number;
    skip: number;
    limit: number;
}

export interface MembraneBackendEventList {
    items: MembraneBackendEvent[];
    total: number;
    skip: number;
    limit: number;
}

@Injectable({ providedIn: 'root' })
export class MembraneBackendService {
    private http = inject(HttpClient);

    /** List Membrane connections for a user (returns first active one). */
    getConnection(userId: string, integrationKey?: string): Observable<MembraneBackendConnection> {
        let url = `${API_URL}/membrane/connections/by-user/${userId}`;
        if (integrationKey) {
            url += `?integration_key=${encodeURIComponent(integrationKey)}`;
        }
        return this.http.get<MembraneBackendConnection>(url);
    }

    /** List emails from Membrane backend. */
    getEmails(userId: string, skip = 0, limit = 20, folder?: string, search?: string): Observable<MembraneBackendEmailList> {
        const params: Record<string, string> = { user_id: userId, skip: String(skip), limit: String(limit) };
        if (folder) params['folder'] = folder;
        if (search) params['search'] = search;
        return this.http.get<MembraneBackendEmailList>(`${API_URL}/membrane/emails`, { params });
    }

    /** List events from Membrane backend. */
    getEvents(userId: string, skip = 0, limit = 20, fromDate?: string, toDate?: string): Observable<MembraneBackendEventList> {
        const params: Record<string, string> = { user_id: userId, skip: String(skip), limit: String(limit) };
        if (fromDate) params['from_date'] = fromDate;
        if (toDate) params['to_date'] = toDate;
        return this.http.get<MembraneBackendEventList>(`${API_URL}/membrane/events`, { params });
    }

    /** Trigger a Membrane action (e.g. sync emails) — delegates to B4F. */
    runAction(actionKey: string, body: { input?: Record<string, unknown>; connection_id?: string }): Observable<{ success: boolean; output?: Record<string, unknown>; error?: string }> {
        return this.http.post<{ success: boolean; output?: Record<string, unknown>; error?: string }>(
            `${API_URL}/membrane/actions/${actionKey}/run`,
            body,
        );
    }
}
