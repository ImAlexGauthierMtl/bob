import { createAction, props } from '@ngrx/store';
import { PlatformOverview } from '../../shared/services/platform-b4f.service';

export const loadPlatformOverview = createAction('[Platform] Load overview');
export const loadPlatformOverviewSuccess = createAction('[Platform] Load overview success', props<{ data: PlatformOverview }>());
export const loadPlatformOverviewFailure = createAction('[Platform] Load overview failure', props<{ error: string }>());
