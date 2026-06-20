import '@angular/compiler';
import { describe, expect, it } from 'vitest';
import {
    createBobRuntimeTool,
    loadBobAssistantSettingsSuccess,
    saveBobAssistantSettings,
    saveBobAssistantSettingsSuccess,
    updateBobRuntimeSettingsSuccess,
} from './bob-assistant-settings.actions';
import {
    bobAssistantSettingsReducer,
    initialBobAssistantSettingsState,
} from './bob-assistant-settings.reducer';

const personality = {
    tone: 'professional',
    formality: 0.5,
    response_length: 'balanced',
    language: 'auto',
    creativity: 0.3,
    emoji_usage: false,
};

const voice = {
    voice: 'autumn',
    speed: 1,
    auto_listen: true,
};

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

describe('bobAssistantSettingsReducer', () => {
    it('loads conversation and voice settings', () => {
        const state = bobAssistantSettingsReducer(initialBobAssistantSettingsState, loadBobAssistantSettingsSuccess({
            personality,
            voice,
            availableTones: ['professional'],
            availableLanguages: [{ code: 'auto', name: 'Auto-detect' }],
            availableVoices: [{ id: 'autumn', name: 'Autumn', gender: 'female', accent: 'North American', style: 'Warm' }],
            runtime,
        }));

        expect(state.personality?.tone).toBe('professional');
        expect(state.voice?.voice).toBe('autumn');
        expect(state.availableVoices.length).toBe(1);
        expect(state.runtime?.providers[0].status).toBe('runtime_backend_managed');
    });

    it('tracks save lifecycle', () => {
        const saving = bobAssistantSettingsReducer(initialBobAssistantSettingsState, saveBobAssistantSettings({
            personality,
            voice,
        }));
        const saved = bobAssistantSettingsReducer(saving, saveBobAssistantSettingsSuccess({
            personality: { ...personality, tone: 'friendly' },
            voice: { ...voice, auto_listen: false },
            availableTones: ['friendly'],
            availableLanguages: [{ code: 'fr', name: 'French' }],
            availableVoices: [{ id: 'marie', name: 'Marie', gender: 'female', accent: 'French Canadian', style: 'Clear' }],
        }));

        expect(saving.saving).toBe(true);
        expect(saved.saving).toBe(false);
        expect(saved.notice).toBe('Settings saved');
        expect(saved.personality?.tone).toBe('friendly');
        expect(saved.voice?.auto_listen).toBe(false);
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
