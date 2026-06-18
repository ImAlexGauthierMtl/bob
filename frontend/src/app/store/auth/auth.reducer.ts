import { createReducer, on } from '@ngrx/store';
import { AuthUser } from '../../shared/models/auth.model';
import { setCurrentUser } from './auth.actions';

export interface AuthState {
    user: AuthUser | null;
}

export const initialAuthState: AuthState = {
    user: null,
};

export const authReducer = createReducer(
    initialAuthState,
    on(setCurrentUser, (state, { user }) => ({ ...state, user })),
);
