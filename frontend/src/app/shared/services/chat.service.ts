import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import { BobChannel } from '../models/bob.model';
import { BobService } from './bob.service';

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    toolSteps?: { tool: string; status: string }[];
}

export interface ChatRequest {
    messages: ChatMessage[];
}

export interface ChatResponse {
    reply: string;
    sessionId: string;
    toolSteps?: { tool: string; status: string }[];
}

@Injectable({ providedIn: 'root' })
export class ChatService {
    constructor(private bob: BobService) {}

    send(message: string, sessionId?: string): Observable<ChatResponse> {
        return this.bob.chat(
            message,
            sessionId,
            undefined,
            { source: 'conversation-page' },
            'workspace' satisfies BobChannel,
        ).pipe(
            map((response) => ({
                reply: response.response,
                sessionId: response.session_id,
                toolSteps: response.tool_steps,
            })),
        );
    }
}
