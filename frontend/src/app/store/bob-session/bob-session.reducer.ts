import { createReducer, on } from '@ngrx/store';
import { setBobSession } from './bob-session.actions';

export interface BobSessionState {
    sessionId: string | null;
}

export const initialBobSessionState: BobSessionState = {
    sessionId: null,
};

export const bobSessionReducer = createReducer(
    initialBobSessionState,
    on(setBobSession, (state, { sessionId }) => ({ ...state, sessionId })),
);
