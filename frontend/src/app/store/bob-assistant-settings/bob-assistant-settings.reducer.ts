import { createReducer, on } from '@ngrx/store';
import {
    BobMemorySettingsResponse,
    BobRuntimeSettingsResponse,
} from '../../shared/services/bob-assistant-settings.service';
import {
    createBobRuntimeAgent,
    createBobRuntimeSkill,
    createBobRuntimeTool,
    loadBobAssistantSettings,
    loadBobAssistantSettingsFailure,
    loadBobAssistantSettingsSuccess,
    updateBobRuntimeSettingsFailure,
    updateBobRuntimeSettingsSuccess,
} from './bob-assistant-settings.actions';

export interface BobAssistantSettingsState {
    runtime: BobRuntimeSettingsResponse | null;
    memorySettings: BobMemorySettingsResponse | null;
    loading: boolean;
    runtimeSaving: boolean;
    error: string | null;
    notice: string | null;
}

export const initialBobAssistantSettingsState: BobAssistantSettingsState = {
    runtime: null,
    memorySettings: null,
    loading: false,
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
