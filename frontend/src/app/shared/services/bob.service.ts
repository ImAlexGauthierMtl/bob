import { environment } from '../../../environments/environment';
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface BobChatRequest {
    message: string;
    session_id?: string;
    mission_prompt?: string;
    mission_context?: Record<string, unknown>;
}

export interface BobChatAction {
    type: string;
    page?: string;
    entity?: string;
    name?: string;
}

export interface BobChatResponse {
    response: string;
    session_id: string;
    turn_count: number;
    actions: BobChatAction[];
}

export interface BobSessionInfo {
    session_id: string;
    user_id: string;
    user_email: string;
    turn_count: number;
    created_at: number;
    last_activity: number;
    message_count: number;
}

const API_URL = `${environment.apiUrl}`;

@Injectable({ providedIn: 'root' })
export class BobService {
    constructor(private http: HttpClient) { }

    chat(message: string, sessionId?: string, missionPrompt?: string, missionContext?: Record<string, unknown>): Observable<BobChatResponse> {
        const body: BobChatRequest = { message };
        if (sessionId) body.session_id = sessionId;
        if (missionPrompt) body.mission_prompt = missionPrompt;
        if (missionContext) body.mission_context = missionContext;
        return this.http.post<BobChatResponse>(`${API_URL}/bob/chat`, body);
    }

    listSessions(): Observable<BobSessionInfo[]> {
        return this.http.get<BobSessionInfo[]>(`${API_URL}/bob/sessions`);
    }

    deleteSession(sessionId: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/bob/sessions/${sessionId}`);
    }
}
