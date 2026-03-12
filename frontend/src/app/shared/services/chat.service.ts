import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

export interface ChatRequest {
    messages: ChatMessage[];
}

export interface ChatResponse {
    reply: string;
}

const API_URL = 'http://localhost:8555/api/v1/chat';

@Injectable({ providedIn: 'root' })
export class ChatService {
    constructor(private http: HttpClient) {}

    send(messages: ChatMessage[]): Observable<ChatResponse> {
        return this.http.post<ChatResponse>(API_URL, { messages });
    }
}
