import { createReducer, on } from '@ngrx/store';
import { CrmDashboardSummary } from '../../shared/services/crm-b4f.service';
import { initialRemoteState, RemoteState } from '../remote-state';
import { loadCrmDashboard, loadCrmDashboardFailure, loadCrmDashboardSuccess } from './crm.actions';

export type CrmState = RemoteState<CrmDashboardSummary>;

export const crmReducer = createReducer(
    initialRemoteState<CrmDashboardSummary>(),
    on(loadCrmDashboard, (state) => ({ ...state, loading: true, error: null })),
    on(loadCrmDashboardSuccess, (_state, { data }) => ({ data, loading: false, error: null })),
    on(loadCrmDashboardFailure, (state, { error }) => ({ ...state, loading: false, error })),
);
