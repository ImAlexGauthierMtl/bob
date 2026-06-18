import { createAction, props } from '@ngrx/store';
import { CrmDashboardSummary } from '../../shared/services/crm-b4f.service';

export const loadCrmDashboard = createAction('[CRM] Load dashboard');
export const loadCrmDashboardSuccess = createAction('[CRM] Load dashboard success', props<{ data: CrmDashboardSummary }>());
export const loadCrmDashboardFailure = createAction('[CRM] Load dashboard failure', props<{ error: string }>());
