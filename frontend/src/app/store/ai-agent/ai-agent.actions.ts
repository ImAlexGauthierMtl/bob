import { createAction, props } from '@ngrx/store';

export const setBobSession = createAction('[AI Agent] Set Bob session', props<{ sessionId: string | null }>());
