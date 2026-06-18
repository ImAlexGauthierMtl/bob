import { createReducer, on } from '@ngrx/store';
import { CrmDashboardSummary } from '../../shared/services/crm-b4f.service';
import { ActivityListResponse } from '../../shared/models/activity.model';
import { ContactListResponse } from '../../shared/models/contact.model';
import { OpportunityListResponse } from '../../shared/models/opportunity.model';
import { OrganizationListResponse } from '../../shared/models/organization.model';
import { initialRemoteState, RemoteState } from '../remote-state';
import {
    loadCrmActivities,
    loadCrmActivitiesFailure,
    loadCrmActivitiesSuccess,
    loadCrmContacts,
    loadCrmContactsFailure,
    loadCrmContactsSuccess,
    loadCrmDashboard,
    loadCrmDashboardFailure,
    loadCrmDashboardSuccess,
    loadCrmOpportunities,
    loadCrmOpportunitiesFailure,
    loadCrmOpportunitiesSuccess,
    loadCrmOrganizations,
    loadCrmOrganizationsFailure,
    loadCrmOrganizationsSuccess,
} from './crm.actions';

export interface CrmState {
    dashboard: RemoteState<CrmDashboardSummary>;
    organizations: RemoteState<OrganizationListResponse>;
    contacts: RemoteState<ContactListResponse>;
    opportunities: RemoteState<OpportunityListResponse>;
    activities: RemoteState<ActivityListResponse>;
}

const initialCrmState: CrmState = {
    dashboard: initialRemoteState<CrmDashboardSummary>(),
    organizations: initialRemoteState<OrganizationListResponse>(),
    contacts: initialRemoteState<ContactListResponse>(),
    opportunities: initialRemoteState<OpportunityListResponse>(),
    activities: initialRemoteState<ActivityListResponse>(),
};

export const crmReducer = createReducer(
    initialCrmState,
    on(loadCrmDashboard, (state) => ({
        ...state,
        dashboard: { ...state.dashboard, loading: true, error: null },
    })),
    on(loadCrmDashboardSuccess, (state, { data }) => ({
        ...state,
        dashboard: { data, loading: false, error: null },
    })),
    on(loadCrmDashboardFailure, (state, { error }) => ({
        ...state,
        dashboard: { ...state.dashboard, loading: false, error },
    })),
    on(loadCrmOrganizations, (state) => ({
        ...state,
        organizations: { ...state.organizations, loading: true, error: null },
    })),
    on(loadCrmOrganizationsSuccess, (state, { data }) => ({
        ...state,
        organizations: { data, loading: false, error: null },
    })),
    on(loadCrmOrganizationsFailure, (state, { error }) => ({
        ...state,
        organizations: { ...state.organizations, loading: false, error },
    })),
    on(loadCrmContacts, (state) => ({
        ...state,
        contacts: { ...state.contacts, loading: true, error: null },
    })),
    on(loadCrmContactsSuccess, (state, { data }) => ({
        ...state,
        contacts: { data, loading: false, error: null },
    })),
    on(loadCrmContactsFailure, (state, { error }) => ({
        ...state,
        contacts: { ...state.contacts, loading: false, error },
    })),
    on(loadCrmOpportunities, (state) => ({
        ...state,
        opportunities: { ...state.opportunities, loading: true, error: null },
    })),
    on(loadCrmOpportunitiesSuccess, (state, { data }) => ({
        ...state,
        opportunities: { data, loading: false, error: null },
    })),
    on(loadCrmOpportunitiesFailure, (state, { error }) => ({
        ...state,
        opportunities: { ...state.opportunities, loading: false, error },
    })),
    on(loadCrmActivities, (state) => ({
        ...state,
        activities: { ...state.activities, loading: true, error: null },
    })),
    on(loadCrmActivitiesSuccess, (state, { data }) => ({
        ...state,
        activities: { data, loading: false, error: null },
    })),
    on(loadCrmActivitiesFailure, (state, { error }) => ({
        ...state,
        activities: { ...state.activities, loading: false, error },
    })),
);
