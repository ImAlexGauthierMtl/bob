import { createAction, props } from '@ngrx/store';
import { AuthUser } from '../../shared/models/auth.model';

export const setCurrentUser = createAction('[Auth] Set current user', props<{ user: AuthUser | null }>());
