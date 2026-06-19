import { createFeatureSelector, createSelector } from '@ngrx/store';
import { BobPlatformSettingsState } from './bob-platform-settings.reducer';

export const selectBobPlatformSettingsState =
    createFeatureSelector<BobPlatformSettingsState>('bobPlatformSettings');

export const selectBobPlatformSettingsData = createSelector(
    selectBobPlatformSettingsState,
    (state) => state.data,
);

export const selectBobPlatformSettingsLoading = createSelector(
    selectBobPlatformSettingsState,
    (state) => state.loading,
);

export const selectBobPlatformSettingsSaving = createSelector(
    selectBobPlatformSettingsState,
    (state) => state.saving,
);

export const selectBobPlatformSettingsError = createSelector(
    selectBobPlatformSettingsState,
    (state) => state.error,
);

export const selectBobPlatformSettingsNotice = createSelector(
    selectBobPlatformSettingsState,
    (state) => state.notice,
);
