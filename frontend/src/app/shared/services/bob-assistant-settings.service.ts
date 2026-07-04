import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

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

export interface KnowledgeDatabase {
    id: string;
    name: string;
    display_name: string;
    description: string;
    status: string;
    milvus_database: string;
    embedding_provider: string;
    embedding_model: string;
    embedding_dimension: number;
    created_by: string;
    created_at: string;
}

export interface KnowledgeCollection {
    id: string;
    database_id: string;
    name: string;
    display_name: string;
    theme: string;
    description: string;
    status: string;
    milvus_collection: string;
    scope_type: string;
    source_kind: string;
    created_by: string;
    created_at: string;
}

export interface KnowledgeSource {
    id: string;
    collection_id: string;
    name: string;
    provider: string;
    source_type: string;
    status: string;
    pipedream_app: string;
    pipedream_source_id?: string | null;
    sync_mode: string;
    ingestion_strategy: string;
    created_by: string;
    created_at: string;
}

export interface KnowledgeOverviewResponse {
    databases: KnowledgeDatabase[];
    collections: KnowledgeCollection[];
    sources: KnowledgeSource[];
    ingestion_flow: string[];
    postgres_source_of_truth: boolean;
    milvus_role: string;
}

export interface BobRuntimeCreateResponse<T> {
    item: T;
    runtime: BobRuntimeSettingsResponse;
}

@Injectable({ providedIn: 'root' })
export class BobAssistantSettingsService {
    private http = inject(HttpClient);
    private baseUrl = environment.bobSettingsApiUrl;

    getRuntime(): Observable<BobRuntimeSettingsResponse> {
        return this.http.get<BobRuntimeSettingsResponse>(`${this.baseUrl}/runtime`);
    }

    getMemory(): Observable<BobMemorySettingsResponse> {
        return this.http.get<BobMemorySettingsResponse>(`${this.baseUrl}/memory`);
    }

    getKnowledge(): Observable<KnowledgeOverviewResponse> {
        return this.http.get<KnowledgeOverviewResponse>(`${this.baseUrl}/knowledge`);
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

    createKnowledgeDatabase(payload: Partial<KnowledgeDatabase> & { name: string; display_name: string }): Observable<KnowledgeDatabase> {
        return this.http.post<KnowledgeDatabase>(
            `${this.baseUrl}/knowledge/databases`,
            payload,
            { headers: this.idempotencyHeaders('knowledge-db') },
        );
    }

    createKnowledgeCollection(payload: Partial<KnowledgeCollection> & { database_id: string; name: string; display_name: string; milvus_collection: string }): Observable<KnowledgeCollection> {
        return this.http.post<KnowledgeCollection>(
            `${this.baseUrl}/knowledge/collections`,
            payload,
            { headers: this.idempotencyHeaders('knowledge-collection') },
        );
    }

    createKnowledgeSource(payload: Partial<KnowledgeSource> & { collection_id: string; name: string }): Observable<KnowledgeSource> {
        return this.http.post<KnowledgeSource>(
            `${this.baseUrl}/knowledge/sources`,
            payload,
            { headers: this.idempotencyHeaders('knowledge-source') },
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
