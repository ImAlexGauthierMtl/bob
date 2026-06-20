import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import {
    BobArtifact,
    BobChannel,
    BobChatConfirmationResponse,
    BobChatRequest,
    BobChatResponse,
    BobChatV1Response,
    BobChatV1Session,
    BobChatV1SessionList,
    BobSessionInfo,
} from '../models/bob.model';

const API_URL = environment.bobChatApiUrl;

@Injectable({ providedIn: 'root' })
export class BobService {
    private http = inject(HttpClient);

    sendMessageV1(body: BobChatRequest): Observable<BobChatV1Response> {
        return this.http.post<BobChatV1Response>(`${API_URL}/messages`, body, {
            headers: new HttpHeaders({
                'Idempotency-Key': this.createIdempotencyKey(),
            }),
        });
    }

    listSessionsV1(): Observable<BobChatV1Session[]> {
        return this.http
            .get<BobChatV1SessionList>(`${API_URL}/sessions`)
            .pipe(map((response) => response.items));
    }

    chat(
        message: string,
        sessionId?: string,
        missionPrompt?: string,
        missionContext?: Record<string, unknown>,
        channel?: BobChannel,
        agentId?: string,
    ): Observable<BobChatResponse> {
        const body: BobChatRequest = { message };
        if (sessionId) body.session_id = sessionId;
        if (channel) body.channel = channel;
        if (agentId) body.agent_id = agentId;
        if (missionPrompt || missionContext) {
            body.mission = {
                prompt: missionPrompt,
                context: missionContext,
            };
        }
        body.client_context = {
            source: 'cde-angular',
            channel: channel || 'compact',
        };

        return this.sendMessageV1(body).pipe(map((response) => this.toBobChatResponse(response)));
    }

    listSessions(): Observable<BobSessionInfo[]> {
        return this.listSessionsV1().pipe(map((sessions) => sessions.map((session) => this.toBobSessionInfo(session))));
    }

    deleteSession(sessionId: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/sessions/${sessionId}`);
    }

    confirmAction(runId: string, confirmationId: string): Observable<BobChatConfirmationResponse> {
        return this.http.post<BobChatConfirmationResponse>(
            `${API_URL}/runs/${runId}/confirmations/${confirmationId}/confirm`,
            {},
            {
                headers: new HttpHeaders({
                    'Idempotency-Key': this.createIdempotencyKey(),
                }),
            },
        );
    }

    cancelAction(runId: string, confirmationId: string): Observable<BobChatConfirmationResponse> {
        return this.http.post<BobChatConfirmationResponse>(
            `${API_URL}/runs/${runId}/confirmations/${confirmationId}/cancel`,
            {},
            {
                headers: new HttpHeaders({
                    'Idempotency-Key': this.createIdempotencyKey(),
                }),
            },
        );
    }

    private toBobChatResponse(response: BobChatV1Response): BobChatResponse {
        const artifact = this.firstArtifact(response.artifacts);
        return {
            response: response.message.content,
            session_id: response.session.id,
            turn_count: response.session.turn_count,
            actions: response.actions || [],
            tool_steps: response.narration_steps
                ?.filter((step) => step.safe_to_show)
                .map((step) => ({ tool: step.label, status: step.status })),
            artifact,
            session_title: response.session.title,
        };
    }

    private toBobSessionInfo(session: BobChatV1Session): BobSessionInfo {
        return {
            session_id: session.id,
            user_id: '',
            user_email: '',
            turn_count: session.turn_count,
            created_at: this.toEpochSeconds(session.created_at),
            last_activity: this.toEpochSeconds(session.updated_at),
            message_count: session.turn_count,
            title: session.title,
        };
    }

    private firstArtifact(artifacts?: BobArtifact[]): BobArtifact | undefined {
        return artifacts && artifacts.length > 0 ? artifacts[0] : undefined;
    }

    private toEpochSeconds(value: string): number {
        const parsed = Date.parse(value);
        return Number.isFinite(parsed) ? Math.floor(parsed / 1000) : Math.floor(Date.now() / 1000);
    }

    private createIdempotencyKey(): string {
        if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
            return crypto.randomUUID();
        }

        return `bob-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }
}
