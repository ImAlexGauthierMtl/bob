import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { BobChatRequest, BobChatResponse, BobSessionInfo } from '../models/bob.model';

const API_URL = `${environment.apiUrl}`;

@Injectable({ providedIn: 'root' })
export class BobService {
    private http = inject(HttpClient);

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
