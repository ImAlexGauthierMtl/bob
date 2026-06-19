import { createFeatureSelector, createSelector } from '@ngrx/store';
import { BccInterviewChatState } from './bcc-interview-chat.reducer';

export const selectBccInterviewChatState =
    createFeatureSelector<BccInterviewChatState>('bccInterviewChat');

export const selectBccInterviewChatMessages = createSelector(
    selectBccInterviewChatState,
    (state) => state.messages,
);

export const selectBccInterviewChatLoading = createSelector(
    selectBccInterviewChatState,
    (state) => state.loading,
);

export const selectBccInterviewChatSessionId = createSelector(
    selectBccInterviewChatState,
    (state) => state.sessionId || undefined,
);

export const selectBccInterviewChatMissionSent = createSelector(
    selectBccInterviewChatState,
    (state) => state.missionSent,
);

export const selectBccInterviewChatPendingSpeech = createSelector(
    selectBccInterviewChatState,
    (state) => state.pendingSpeech,
);

export const selectBccInterviewChatError = createSelector(
    selectBccInterviewChatState,
    (state) => state.error,
);
