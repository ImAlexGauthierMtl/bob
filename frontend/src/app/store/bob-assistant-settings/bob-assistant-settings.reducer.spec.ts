import '@angular/compiler';
import { describe, expect, it } from 'vitest';
import {
    createBobRuntimeTool,
    loadBobAssistantSettingsSuccess,
    updateBobRuntimeSettingsSuccess,
} from './bob-assistant-settings.actions';
import {
    bobAssistantSettingsReducer,
    initialBobAssistantSettingsState,
} from './bob-assistant-settings.reducer';

const runtime = {
    providers: [{
        id: 'fireworks-kimi',
        name: 'Fireworks Kimi K2.7 Code',
        provider: 'fireworks',
        model: 'accounts/fireworks/models/kimi-k2p7-code',
        status: 'runtime_backend_managed',
        enabled: true,
    }],
    active_provider: 'auto',
    agents: [],
    skills: [],
    tools: [],
    memory: {},
};

const memorySettings = {
    status: {
        tenant_id: 'tenant-croo-local',
        user_id: 'user-local',
        database_status: 'ready',
        memory_entries: 2,
        organization_entries: 1,
        journal_entries: 1,
        last_event: null,
        isolation_enforced: true,
    },
    vector_index: {
        config: {
            provider: 'milvus',
            enabled: true,
            configured: true,
            uri_configured: true,
            token_configured: true,
            database: 'default',
            secure: true,
            timeout_seconds: 5,
            default_dimension: 1024,
            embedding_provider: 'fireworks',
            embedding_model_configured: true,
            embedding_dimension: 1024,
            embedding_configured: true,
        },
        health: {
            provider: 'milvus',
            status: 'ready',
            ready: true,
            checked: true,
            enabled: true,
            configured: true,
            embedding_configured: true,
            failure_code: null,
        },
        degraded: [],
    },
    rag: {
        postgres_source_of_truth: true,
        milvus_role: 'reconstructible_index',
        content_revalidation: 'postgres_before_context',
        available_context_routes: ['rag/context'],
    },
    source: 'agent-memory-backend-api',
};

describe('bobAssistantSettingsReducer', () => {
    it('loads runtime and memory settings', () => {
        const state = bobAssistantSettingsReducer(initialBobAssistantSettingsState, loadBobAssistantSettingsSuccess({
            runtime,
            memorySettings,
        }));

        expect(state.runtime?.providers[0].status).toBe('runtime_backend_managed');
        expect(state.memorySettings?.status?.database_status).toBe('ready');
    });

    it('tracks runtime catalog mutations', () => {
        const creating = bobAssistantSettingsReducer(initialBobAssistantSettingsState, createBobRuntimeTool({
            tool: { name: 'smoke_tool' },
        }));
        const updated = bobAssistantSettingsReducer(creating, updateBobRuntimeSettingsSuccess({
            runtime: {
                ...runtime,
                tools: [{
                    id: 'tool-smoke',
                    name: 'smoke_tool',
                    family: 'runtime',
                    risk: 'read',
                    status: 'draft',
                    description: '',
                }],
            },
            notice: 'Tool added',
        }));

        expect(creating.runtimeSaving).toBe(true);
        expect(updated.runtimeSaving).toBe(false);
        expect(updated.notice).toBe('Tool added');
        expect(updated.runtime?.tools[0].name).toBe('smoke_tool');
    });
});
