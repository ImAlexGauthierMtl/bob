import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
    MS365Connection,
    MS365AuthUrl,
    SyncedEmailListResponse,
    SyncedEventListResponse,
    SyncedEmail,
    SyncedEvent,
    SyncStatus,
    EmailAiInsightResponse,
    SendEmailRequest,
    ReplyEmailRequest,
    ForwardEmailRequest
} from '../models/ms365.model';

const API_URL = `${environment.apiUrl}`;

@Injectable({ providedIn: 'root' })
export class MS365Service {
    private http = inject(HttpClient);

    /** Get OAuth2 authorization URL to redirect user to Microsoft login */
    getAuthUrl(): Observable<MS365AuthUrl> {
        return this.http.get<MS365AuthUrl>(`${API_URL}/ms365/auth-url`);
    }

    /** Get current user's MS365 connection status */
    getConnection(): Observable<MS365Connection | null> {
        return this.http.get<MS365Connection | null>(`${API_URL}/ms365/connection`);
    }

    /** Disconnect MS365 integration */
    disconnect(): Observable<void> {
        return this.http.delete<void>(`${API_URL}/ms365/connection`);
    }

    /** Force an immediate sync of emails and calendar */
    triggerSync(): Observable<SyncStatus> {
        return this.http.post<SyncStatus>(`${API_URL}/ms365/sync`, {});
    }

    /** List synced emails with pagination and optional filters */
    getEmails(skip = 0, limit = 50, folder?: string, search?: string, smartLabel?: string, linkedContactId?: string): Observable<SyncedEmailListResponse> {
        let url = `${API_URL}/ms365/emails?skip=${skip}&limit=${limit}`;
        if (folder) url += `&folder=${folder}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (smartLabel) url += `&smart_label=${encodeURIComponent(smartLabel)}`;
        if (linkedContactId) url += `&linked_contact_id=${linkedContactId}`;
        return this.http.get<SyncedEmailListResponse>(url);
    }

    /** Get a specific synced email */
    getEmail(id: string): Observable<SyncedEmail> {
        return this.http.get<SyncedEmail>(`${API_URL}/ms365/emails/${id}`);
    }

    /** Generate AI Insights for an email */
    generateEmailAiInsights(id: string): Observable<EmailAiInsightResponse> {
        return this.http.post<EmailAiInsightResponse>(`${API_URL}/ms365/emails/${id}/ai-insights`, {});
    }

    /** Send a new email */
    sendEmail(request: SendEmailRequest): Observable<{ status: string }> {
        return this.http.post<{ status: string }>(`${API_URL}/ms365/emails/send`, request);
    }

    /** Reply to an email */
    replyEmail(id: string, request: ReplyEmailRequest): Observable<{ status: string }> {
        return this.http.post<{ status: string }>(`${API_URL}/ms365/emails/${id}/reply`, request);
    }

    /** Forward an email */
    forwardEmail(id: string, request: ForwardEmailRequest): Observable<{ status: string }> {
        return this.http.post<{ status: string }>(`${API_URL}/ms365/emails/${id}/forward`, request);
    }

    /** List synced calendar events with pagination and optional date range */
    getEvents(skip = 0, limit = 50, fromDate?: string, toDate?: string): Observable<SyncedEventListResponse> {
        let url = `${API_URL}/ms365/events?skip=${skip}&limit=${limit}`;
        if (fromDate) url += `&from_date=${fromDate}`;
        if (toDate) url += `&to_date=${toDate}`;
        return this.http.get<SyncedEventListResponse>(url);
    }

    /** Get a specific synced calendar event */
    getEvent(id: string): Observable<SyncedEvent> {
        return this.http.get<SyncedEvent>(`${API_URL}/ms365/events/${id}`);
    }
}
