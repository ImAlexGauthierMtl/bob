import { createAction, props } from '@ngrx/store';
import {
    CrmActivitiesQuery,
    CrmContactsQuery,
    CrmDashboardSummary,
    CrmListQuery,
    CrmOpportunitiesQuery,
} from '../../shared/services/crm-b4f.service';
import { ActivityListResponse } from '../../shared/models/activity.model';
import { ContactListResponse } from '../../shared/models/contact.model';
import { OpportunityListResponse } from '../../shared/models/opportunity.model';
import { OrganizationListResponse } from '../../shared/models/organization.model';

export const loadCrmDashboard = createAction('[CRM] Load dashboard');
export const loadCrmDashboardSuccess = createAction('[CRM] Load dashboard success', props<{ data: CrmDashboardSummary }>());
export const loadCrmDashboardFailure = createAction('[CRM] Load dashboard failure', props<{ error: string }>());

export const loadCrmOrganizations = createAction('[CRM] Load organizations', props<CrmListQuery>());
export const loadCrmOrganizationsSuccess = createAction('[CRM] Load organizations success', props<{ data: OrganizationListResponse }>());
export const loadCrmOrganizationsFailure = createAction('[CRM] Load organizations failure', props<{ error: string }>());

export const loadCrmContacts = createAction('[CRM] Load contacts', props<CrmContactsQuery>());
export const loadCrmContactsSuccess = createAction('[CRM] Load contacts success', props<{ data: ContactListResponse }>());
export const loadCrmContactsFailure = createAction('[CRM] Load contacts failure', props<{ error: string }>());

export const loadCrmOpportunities = createAction('[CRM] Load opportunities', props<CrmOpportunitiesQuery>());
export const loadCrmOpportunitiesSuccess = createAction('[CRM] Load opportunities success', props<{ data: OpportunityListResponse }>());
export const loadCrmOpportunitiesFailure = createAction('[CRM] Load opportunities failure', props<{ error: string }>());

export const loadCrmActivities = createAction('[CRM] Load activities', props<CrmActivitiesQuery>());
export const loadCrmActivitiesSuccess = createAction('[CRM] Load activities success', props<{ data: ActivityListResponse }>());
export const loadCrmActivitiesFailure = createAction('[CRM] Load activities failure', props<{ error: string }>());
