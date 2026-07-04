import { createFeatureSelector, createSelector } from '@ngrx/store';
import { BobAssistantSettingsState } from './bob-assistant-settings.reducer';

export const selectBobAssistantSettingsState =
    createFeatureSelector<BobAssistantSettingsState>('bobAssistantSettings');

export const selectBobAssistantRuntimeSettings = createSelector(
    selectBobAssistantSettingsState,
    (state) => state.runtime,
);

export const selectBobAssistantMemorySettings = createSelector(
    selectBobAssistantSettingsState,
    (state) => state.memorySettings,
);

export const selectBobAssistantSettingsLoading = createSelector(
    selectBobAssistantSettingsState,
    (state) => state.loading,
);

export const selectBobAssistantRuntimeSaving = createSelector(
    selectBobAssistantSettingsState,
    (state) => state.runtimeSaving,
);

export const selectBobAssistantSettingsNotice = createSelector(
    selectBobAssistantSettingsState,
    (state) => state.notice,
);

export const selectBobAssistantSettingsError = createSelector(
    selectBobAssistantSettingsState,
    (state) => state.error,
);
