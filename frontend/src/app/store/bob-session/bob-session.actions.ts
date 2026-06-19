import { createAction, props } from '@ngrx/store';

export const setBobSession = createAction('[Bob Session] Set session', props<{ sessionId: string | null }>());
