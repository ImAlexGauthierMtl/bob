import { createReducer, on } from '@ngrx/store';
import { setBobSession } from './ai-agent.actions';

export interface AiAgentState {
    sessionId: string | null;
}

export const initialAiAgentState: AiAgentState = {
    sessionId: null,
};

export const aiAgentReducer = createReducer(
    initialAiAgentState,
    on(setBobSession, (state, { sessionId }) => ({ ...state, sessionId })),
);
