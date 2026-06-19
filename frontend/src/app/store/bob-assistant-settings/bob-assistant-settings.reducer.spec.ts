import '@angular/compiler';
import { describe, expect, it } from 'vitest';
import {
    loadBobAssistantSettingsSuccess,
    saveBobAssistantSettings,
    saveBobAssistantSettingsSuccess,
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

describe('bobAssistantSettingsReducer', () => {
    it('loads conversation and voice settings', () => {
        const state = bobAssistantSettingsReducer(initialBobAssistantSettingsState, loadBobAssistantSettingsSuccess({
            personality,
            voice,
            availableTones: ['professional'],
            availableLanguages: [{ code: 'auto', name: 'Auto-detect' }],
            availableVoices: [{ id: 'autumn', name: 'Autumn', gender: 'female', accent: 'North American', style: 'Warm' }],
        }));

        expect(state.personality?.tone).toBe('professional');
        expect(state.voice?.voice).toBe('autumn');
        expect(state.availableVoices.length).toBe(1);
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
});
