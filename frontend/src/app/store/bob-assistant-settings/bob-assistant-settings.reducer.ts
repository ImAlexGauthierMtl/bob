import { createReducer, on } from '@ngrx/store';
import {
    BobConversationPersonality,
    BobLanguageOption,
    BobMemorySettingsResponse,
    BobRuntimeSettingsResponse,
    BobVoiceOption,
    BobVoiceSettings,
} from '../../shared/services/bob-assistant-settings.service';
import {
    createBobRuntimeAgent,
    createBobRuntimeSkill,
    createBobRuntimeTool,
    loadBobAssistantSettings,
    loadBobAssistantSettingsFailure,
    loadBobAssistantSettingsSuccess,
    saveBobAssistantSettings,
    saveBobAssistantSettingsFailure,
    saveBobAssistantSettingsSuccess,
    updateBobRuntimeSettingsFailure,
    updateBobRuntimeSettingsSuccess,
} from './bob-assistant-settings.actions';

export interface BobAssistantSettingsState {
    personality: BobConversationPersonality | null;
    voice: BobVoiceSettings | null;
    availableTones: string[];
    availableLanguages: BobLanguageOption[];
    availableVoices: BobVoiceOption[];
    runtime: BobRuntimeSettingsResponse | null;
    memorySettings: BobMemorySettingsResponse | null;
    loading: boolean;
    saving: boolean;
    runtimeSaving: boolean;
    error: string | null;
    notice: string | null;
}

export const initialBobAssistantSettingsState: BobAssistantSettingsState = {
    personality: null,
    voice: null,
    availableTones: [],
    availableLanguages: [],
    availableVoices: [],
    runtime: null,
    memorySettings: null,
    loading: false,
    saving: false,
    runtimeSaving: false,
    error: null,
    notice: null,
};

export const bobAssistantSettingsReducer = createReducer(
    initialBobAssistantSettingsState,
    on(loadBobAssistantSettings, (state) => ({ ...state, loading: true, error: null, notice: null })),
    on(loadBobAssistantSettingsSuccess, (state, payload) => ({
        ...state,
        ...payload,
        loading: false,
        error: null,
    })),
    on(loadBobAssistantSettingsFailure, (state, { error }) => ({
        ...state,
        loading: false,
        error,
    })),
    on(saveBobAssistantSettings, (state) => ({ ...state, saving: true, error: null, notice: null })),
    on(saveBobAssistantSettingsSuccess, (state, payload) => ({
        ...state,
        ...payload,
        saving: false,
        error: null,
        notice: 'Settings saved',
    })),
    on(saveBobAssistantSettingsFailure, (state, { error }) => ({
        ...state,
        saving: false,
        error,
        notice: 'Error saving settings',
    })),
    on(createBobRuntimeAgent, createBobRuntimeSkill, createBobRuntimeTool, (state) => ({
        ...state,
        runtimeSaving: true,
        error: null,
        notice: null,
    })),
    on(updateBobRuntimeSettingsSuccess, (state, { runtime, notice }) => ({
        ...state,
        runtime,
        runtimeSaving: false,
        error: null,
        notice,
    })),
    on(updateBobRuntimeSettingsFailure, (state, { error }) => ({
        ...state,
        runtimeSaving: false,
        error,
        notice: 'Runtime settings error',
    })),
);
