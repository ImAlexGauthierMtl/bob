import { createAction, props } from '@ngrx/store';
import { CommunicationIntegrationOverview } from '../../shared/services/communication-b4f.service';

export const loadCommunicationOverview = createAction('[Communication] Load overview');
export const loadCommunicationOverviewSuccess = createAction('[Communication] Load overview success', props<{ data: CommunicationIntegrationOverview }>());
export const loadCommunicationOverviewFailure = createAction('[Communication] Load overview failure', props<{ error: string }>());
