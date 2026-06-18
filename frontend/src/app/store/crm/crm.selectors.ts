import { createSelector } from '@ngrx/store';
import type { AppState } from '..';

export const selectCrmState = (state: AppState) => state.crm;

const selectCrmDashboardState = createSelector(
    selectCrmState,
    (state) => state.dashboard,
);

export const selectCrmDashboard = createSelector(
    selectCrmDashboardState,
    (state) => state.data,
);

export const selectCrmLoading = createSelector(
    selectCrmDashboardState,
    (state) => state.loading,
);

export const selectCrmError = createSelector(
    selectCrmDashboardState,
    (state) => state.error,
);

export const selectCrmOrganizationsState = createSelector(
    selectCrmState,
    (state) => state.organizations,
);

export const selectCrmOrganizations = createSelector(
    selectCrmOrganizationsState,
    (state) => state.data?.items ?? [],
);

export const selectCrmOrganizationsTotal = createSelector(
    selectCrmOrganizationsState,
    (state) => state.data?.total ?? 0,
);

export const selectCrmOrganizationsLoading = createSelector(
    selectCrmOrganizationsState,
    (state) => state.loading,
);

export const selectCrmOrganizationsError = createSelector(
    selectCrmOrganizationsState,
    (state) => state.error,
);

export const selectCrmContactsState = createSelector(
    selectCrmState,
    (state) => state.contacts,
);

export const selectCrmContacts = createSelector(
    selectCrmContactsState,
    (state) => state.data?.items ?? [],
);

export const selectCrmContactsTotal = createSelector(
    selectCrmContactsState,
    (state) => state.data?.total ?? 0,
);

export const selectCrmContactsLoading = createSelector(
    selectCrmContactsState,
    (state) => state.loading,
);

export const selectCrmContactsError = createSelector(
    selectCrmContactsState,
    (state) => state.error,
);

export const selectCrmOpportunitiesState = createSelector(
    selectCrmState,
    (state) => state.opportunities,
);

export const selectCrmOpportunities = createSelector(
    selectCrmOpportunitiesState,
    (state) => state.data?.items ?? [],
);

export const selectCrmOpportunitiesTotal = createSelector(
    selectCrmOpportunitiesState,
    (state) => state.data?.total ?? 0,
);

export const selectCrmOpportunitiesLoading = createSelector(
    selectCrmOpportunitiesState,
    (state) => state.loading,
);

export const selectCrmOpportunitiesError = createSelector(
    selectCrmOpportunitiesState,
    (state) => state.error,
);

export const selectCrmActivitiesState = createSelector(
    selectCrmState,
    (state) => state.activities,
);

export const selectCrmActivities = createSelector(
    selectCrmActivitiesState,
    (state) => state.data?.items ?? [],
);

export const selectCrmActivitiesTotal = createSelector(
    selectCrmActivitiesState,
    (state) => state.data?.total ?? 0,
);

export const selectCrmActivitiesLoading = createSelector(
    selectCrmActivitiesState,
    (state) => state.loading,
);

export const selectCrmActivitiesError = createSelector(
    selectCrmActivitiesState,
    (state) => state.error,
);
