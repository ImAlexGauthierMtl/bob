import { createSelector } from '@ngrx/store';
import type { AppState } from '..';

export const selectCrmState = (state: AppState) => state.crm;

export const selectCrmDashboard = createSelector(
    selectCrmState,
    (state) => state.data,
);

export const selectCrmLoading = createSelector(
    selectCrmState,
    (state) => state.loading,
);

export const selectCrmError = createSelector(
    selectCrmState,
    (state) => state.error,
);
