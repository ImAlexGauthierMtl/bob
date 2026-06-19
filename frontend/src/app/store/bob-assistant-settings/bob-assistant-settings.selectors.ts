import { createFeatureSelector, createSelector } from '@ngrx/store';
import { BobAssistantSettingsState } from './bob-assistant-settings.reducer';

export const selectBobAssistantSettingsState =
    createFeatureSelector<BobAssistantSettingsState>('bobAssistantSettings');

export const selectBobAssistantSettingsPersonality = createSelector(
    selectBobAssistantSettingsState,
    (state) => state.personality,
);

export const selectBobAssistantSettingsVoice = createSelector(
    selectBobAssistantSettingsState,
    (state) => state.voice,
);

export const selectBobAssistantSettingsOptions = createSelector(
    selectBobAssistantSettingsState,
    (state) => ({
        availableTones: state.availableTones,
        availableLanguages: state.availableLanguages,
        availableVoices: state.availableVoices,
    }),
);

export const selectBobAssistantSettingsLoading = createSelector(
    selectBobAssistantSettingsState,
    (state) => state.loading,
);

export const selectBobAssistantSettingsSaving = createSelector(
    selectBobAssistantSettingsState,
    (state) => state.saving,
);

export const selectBobAssistantSettingsNotice = createSelector(
    selectBobAssistantSettingsState,
    (state) => state.notice,
);

export const selectBobAssistantSettingsError = createSelector(
    selectBobAssistantSettingsState,
    (state) => state.error,
);
