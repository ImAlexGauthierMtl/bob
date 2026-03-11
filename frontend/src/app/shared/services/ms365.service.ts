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
    getEmails(skip = 0, limit = 50, folder?: string, search?: string): Observable<SyncedEmailListResponse> {
        let url = `${API_URL}/ms365/emails?skip=${skip}&limit=${limit}`;
        if (folder) url += `&folder=${folder}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        return this.http.get<SyncedEmailListResponse>(url);
    }

    /** Get a specific synced email */
    getEmail(id: string): Observable<SyncedEmail> {
        return this.http.get<SyncedEmail>(`${API_URL}/ms365/emails/${id}`);
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
