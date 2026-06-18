import { createAction, props } from '@ngrx/store';
import { KbHome } from '../../shared/services/kb-b4f.service';

export const loadKbHome = createAction('[KB] Load home');
export const loadKbHomeSuccess = createAction('[KB] Load home success', props<{ data: KbHome }>());
export const loadKbHomeFailure = createAction('[KB] Load home failure', props<{ error: string }>());
