import '@angular/compiler';
import { describe, expect, it } from 'vitest';
import { setBobSession } from './bob-session.actions';
import { bobSessionReducer, initialBobSessionState } from './bob-session.reducer';

describe('bobSessionReducer', () => {
    it('stores the active Bob session id', () => {
        const state = bobSessionReducer(initialBobSessionState, setBobSession({ sessionId: 'session-1' }));

        expect(state.sessionId).toBe('session-1');
    });

    it('clears the Bob session id', () => {
        const state = bobSessionReducer({ sessionId: 'session-1' }, setBobSession({ sessionId: null }));

        expect(state.sessionId).toBeNull();
    });
});
