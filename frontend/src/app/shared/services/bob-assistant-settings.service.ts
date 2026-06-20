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

export interface BobRuntimeProvider {
    id: string;
    name: string;
    provider: string;
    model: string;
    status: string;
    enabled: boolean;
}

export interface BobRuntimeAgent {
    id: string;
    name: string;
    description: string;
    provider_id: string;
    status: string;
    skills: string[];
    tools: string[];
}

export interface BobRuntimeSkill {
    id: string;
    name: string;
    description: string;
    status: string;
    scope: string;
}

export interface BobRuntimeTool {
    id: string;
    name: string;
    family: string;
    risk: string;
    status: string;
    description: string;
}

export interface BobRuntimeMcpCapability {
    id: string;
    qualified_id: string;
    family: string;
    title?: string;
    file?: string;
    risk?: string;
    skill?: string;
    capability_path?: string;
    tools?: string[];
}

export interface BobRuntimeMcpFamily {
    family: string;
    label?: string;
    description?: string;
    risk?: string;
    skill?: string;
    capabilities?: string;
    capability_count?: number;
    capability_items?: BobRuntimeMcpCapability[];
}

export interface BobRuntimeMcpSettings {
    local_only?: boolean;
    tool_gating_required?: boolean;
    max_normal_families?: number;
    max_exceptional_families?: number;
    families: BobRuntimeMcpFamily[];
    capabilities: BobRuntimeMcpCapability[];
}

export interface BobRuntimeSettingsResponse {
    providers: BobRuntimeProvider[];
    active_provider: string;
    agents: BobRuntimeAgent[];
    skills: BobRuntimeSkill[];
    tools: BobRuntimeTool[];
    memory: Record<string, string>;
    mcp?: BobRuntimeMcpSettings;
    source?: string;
}

export interface BobRuntimeCreateResponse<T> {
    item: T;
    runtime: BobRuntimeSettingsResponse;
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

    getRuntime(): Observable<BobRuntimeSettingsResponse> {
        return this.http.get<BobRuntimeSettingsResponse>(`${this.baseUrl}/runtime`);
    }

    createRuntimeAgent(payload: Partial<BobRuntimeAgent> & { name: string }): Observable<BobRuntimeCreateResponse<BobRuntimeAgent>> {
        return this.http.post<BobRuntimeCreateResponse<BobRuntimeAgent>>(
            `${this.baseUrl}/runtime/agents`,
            payload,
            { headers: this.idempotencyHeaders('runtime-agent') },
        );
    }

    createRuntimeSkill(payload: Partial<BobRuntimeSkill> & { name: string }): Observable<BobRuntimeCreateResponse<BobRuntimeSkill>> {
        return this.http.post<BobRuntimeCreateResponse<BobRuntimeSkill>>(
            `${this.baseUrl}/runtime/skills`,
            payload,
            { headers: this.idempotencyHeaders('runtime-skill') },
        );
    }

    createRuntimeTool(payload: Partial<BobRuntimeTool> & { name: string }): Observable<BobRuntimeCreateResponse<BobRuntimeTool>> {
        return this.http.post<BobRuntimeCreateResponse<BobRuntimeTool>>(
            `${this.baseUrl}/runtime/tools`,
            payload,
            { headers: this.idempotencyHeaders('runtime-tool') },
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
