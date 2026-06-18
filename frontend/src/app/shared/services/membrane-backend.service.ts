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

import { AttachmentMeta } from '../models/ms365.model';

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
    importance?: string;
    has_attachments: boolean;
    attachments_meta?: AttachmentMeta[] | null;
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

    /** List Pipedream-backed local connections for a user (returns first active one). */
    getConnection(userId: string, integrationKey?: string): Observable<MembraneBackendConnection> {
        let url = `${API_URL}/pipedream/connections/by-user/${userId}`;
        if (integrationKey) {
            url += `?integration_key=${encodeURIComponent(integrationKey)}`;
        }
        return this.http.get<MembraneBackendConnection>(url);
    }

    /** Get a specific synced email from the local integration backend. */
    getEmail(id: string, userId: string): Observable<MembraneBackendEmail> {
        return this.http.get<MembraneBackendEmail>(`${API_URL}/pipedream/emails/${id}?user_id=${userId}`);
    }

    /** List emails from the local integration backend. */
    getEmails(userId: string, skip = 0, limit = 20, folder?: string, search?: string, smartLabel?: string, linkedContactId?: string): Observable<MembraneBackendEmailList> {
        const params: Record<string, string> = { user_id: userId, skip: String(skip), limit: String(limit) };
        if (folder) params['folder'] = folder;
        if (search) params['search'] = search;
        if (smartLabel) params['smart_label'] = smartLabel;
        if (linkedContactId) params['linked_contact_id'] = linkedContactId;
        return this.http.get<MembraneBackendEmailList>(`${API_URL}/pipedream/emails`, { params });
    }

    /** Send a new email via Pipedream backend action. */
    sendEmail(userId: string, request: { subject: string; body_content: string; to_recipients: string[]; cc_recipients?: string[]; bcc_recipients?: string[]; body_type?: string }): Observable<{ status: string }> {
        return this.http.post<{ status: string }>(`${API_URL}/pipedream/emails/send`, { ...request, user_id: userId });
    }

    /** Reply to an email via Pipedream backend action. */
    replyEmail(id: string, userId: string, request: { comment: string; reply_all?: boolean }): Observable<{ status: string }> {
        return this.http.post<{ status: string }>(`${API_URL}/pipedream/emails/${id}/reply`, { ...request, user_id: userId });
    }

    /** Forward an email via Pipedream backend action. */
    forwardEmail(id: string, userId: string, request: { to_recipients: string[]; comment?: string }): Observable<{ status: string }> {
        return this.http.post<{ status: string }>(`${API_URL}/pipedream/emails/${id}/forward`, { ...request, user_id: userId });
    }

    /** Pull recent emails via Pipedream action into the local DB. */
    syncEmails(top = 50): Observable<{ status: string; synced: number; fetched: number; errors: string[] }> {
        return this.http.post<{ status: string; synced: number; fetched: number; errors: string[] }>(
            `${API_URL}/pipedream/sync-emails?top=${top}`,
            {}
        );
    }

    /** List events from the local integration backend. */
    getEvents(userId: string, skip = 0, limit = 20, fromDate?: string, toDate?: string): Observable<MembraneBackendEventList> {
        const params: Record<string, string> = { user_id: userId, skip: String(skip), limit: String(limit) };
        if (fromDate) params['from_date'] = fromDate;
        if (toDate) params['to_date'] = toDate;
        return this.http.get<MembraneBackendEventList>(`${API_URL}/pipedream/events`, { params });
    }

    /** Trigger a Pipedream action (e.g. sync emails) — delegates to B4F. */
    runAction(actionKey: string, body: { input?: Record<string, unknown>; connection_id?: string }): Observable<{ success: boolean; output?: Record<string, unknown>; error?: string }> {
        return this.http.post<{ success: boolean; output?: Record<string, unknown>; error?: string }>(
            `${API_URL}/pipedream/actions/${actionKey}/run`,
            body,
        );
    }
}
