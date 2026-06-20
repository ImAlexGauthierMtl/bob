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
    runtime_status?: string;
    connector_status?: string;
    settings_status?: string;
    remaining_work?: string[];
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
    active_capability_count?: number;
    runtime_status?: string;
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

export interface BobRuntimeConversionModule {
    id: string;
    label: string;
    status: string;
    owner: string;
    controls?: string[];
}

export interface BobRuntimeConversionSurface {
    id: string;
    label: string;
    status: string;
    current: string;
    target: string;
    evidence?: string[];
    remaining_work?: string[];
}

export interface BobRuntimeConversionInventory {
    target: string;
    status: string;
    active_model: string;
    settings_modules: BobRuntimeConversionModule[];
    surfaces: BobRuntimeConversionSurface[];
}

export interface BobRuntimeSettingsResponse {
    providers: BobRuntimeProvider[];
    active_provider: string;
    agents: BobRuntimeAgent[];
    skills: BobRuntimeSkill[];
    tools: BobRuntimeTool[];
    memory: Record<string, string>;
    mcp?: BobRuntimeMcpSettings;
    conversion_inventory?: BobRuntimeConversionInventory;
    source?: string;
}

export interface BobMemoryStatus {
    tenant_id: string;
    user_id: string;
    database_status: string;
    memory_entries: number;
    organization_entries: number;
    journal_entries: number;
    last_event?: string | null;
    isolation_enforced: boolean;
}

export interface BobVectorIndexConfig {
    provider: string;
    enabled: boolean;
    configured: boolean;
    uri_configured: boolean;
    token_configured: boolean;
    database: string;
    secure: boolean;
    timeout_seconds: number;
    default_dimension: number;
    embedding_provider: string;
    embedding_model_configured: boolean;
    embedding_dimension: number;
    embedding_configured: boolean;
}

export interface BobVectorIndexHealth {
    provider: string;
    status: string;
    ready: boolean;
    checked: boolean;
    enabled: boolean;
    configured: boolean;
    embedding_configured: boolean;
    failure_code?: string | null;
}

export interface BobMemoryDegradedStatus {
    target: string;
    status_code: number;
    detail: { code?: string; message?: string } | string | null;
}

export interface BobMemoryRagSettings {
    postgres_source_of_truth: boolean;
    milvus_role: string;
    content_revalidation: string;
    available_context_routes: string[];
}

export interface BobMemorySettingsResponse {
    status: BobMemoryStatus | null;
    vector_index: {
        config: BobVectorIndexConfig | null;
        health: BobVectorIndexHealth | null;
        degraded: BobMemoryDegradedStatus[];
    };
    rag: BobMemoryRagSettings | null;
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

    getMemory(): Observable<BobMemorySettingsResponse> {
        return this.http.get<BobMemorySettingsResponse>(`${this.baseUrl}/memory`);
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
