import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface BobVoiceOption {
    id: string;
    name: string;
    gender: string;
    accent: string;
    style: string;
    provider?: string;
}

export interface BobLanguageOption {
    code: string;
    name: string;
}

export interface BobConversationPersonality {
    tone: string;
    formality: number;
    response_length: string;
    language: string;
    creativity: number;
    emoji_usage: boolean;
}

export interface BobVoiceSettings {
    voice: string;
    speed: number;
    auto_listen: boolean;
}

export interface BobConversationSettingsResponse {
    personality: BobConversationPersonality;
    available_tones: string[];
    available_languages: BobLanguageOption[];
    source?: string;
}

export interface BobVoiceSettingsResponse {
    voice: BobVoiceSettings;
    available_voices: BobVoiceOption[];
    source?: string;
}

@Injectable({ providedIn: 'root' })
export class BobAssistantSettingsService {
    private http = inject(HttpClient);
    private baseUrl = environment.bobSettingsApiUrl;

    getConversation(): Observable<BobConversationSettingsResponse> {
        return this.http.get<BobConversationSettingsResponse>(`${this.baseUrl}/conversation`);
    }

    updateConversation(personality: BobConversationPersonality): Observable<BobConversationSettingsResponse> {
        return this.http.put<BobConversationSettingsResponse>(
            `${this.baseUrl}/conversation`,
            { personality },
            { headers: this.idempotencyHeaders('conversation') },
        );
    }

    getVoice(): Observable<BobVoiceSettingsResponse> {
        return this.http.get<BobVoiceSettingsResponse>(`${this.baseUrl}/voice`);
    }

    updateVoice(voice: BobVoiceSettings): Observable<BobVoiceSettingsResponse> {
        return this.http.put<BobVoiceSettingsResponse>(
            `${this.baseUrl}/voice`,
            { voice },
            { headers: this.idempotencyHeaders('voice') },
        );
    }

    private idempotencyHeaders(prefix: string): HttpHeaders {
        return new HttpHeaders({ 'Idempotency-Key': `${prefix}-${this.randomId()}` });
    }

    private randomId(): string {
        if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
            return crypto.randomUUID();
        }
        return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    }
}
