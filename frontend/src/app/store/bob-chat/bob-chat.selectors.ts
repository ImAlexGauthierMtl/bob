import { createFeatureSelector, createSelector } from '@ngrx/store';
import { BobChatSessionGroup } from './bob-chat.models';
import { BobChatState } from './bob-chat.reducer';

export const selectBobChatState = createFeatureSelector<BobChatState>('bobChat');

export const selectBobChatMessages = createSelector(
    selectBobChatState,
    (state) => state.messages,
);

export const selectBobChatSessions = createSelector(
    selectBobChatState,
    (state) => state.sessions,
);

export const selectBobChatSessionGroups = createSelector(
    selectBobChatSessions,
    (sessions): BobChatSessionGroup[] => {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
        const yesterday = today - 86400000;
        const weekAgo = today - 7 * 86400000;
        const groups: BobChatSessionGroup[] = [
            { label: 'Today', sessions: [] },
            { label: 'Yesterday', sessions: [] },
            { label: 'Last 7 Days', sessions: [] },
            { label: 'Older', sessions: [] },
        ];

        for (const session of sessions) {
            const ts = session.updatedAt.getTime();
            if (ts >= today) {
                groups[0].sessions.push(session);
            } else if (ts >= yesterday) {
                groups[1].sessions.push(session);
            } else if (ts >= weekAgo) {
                groups[2].sessions.push(session);
            } else {
                groups[3].sessions.push(session);
            }
        }

        return groups.filter((group) => group.sessions.length > 0);
    },
);

export const selectBobChatSessionId = createSelector(
    selectBobChatState,
    (state) => state.sessionId || undefined,
);

export const selectBobChatActiveTitle = createSelector(
    selectBobChatState,
    (state) => state.activeTitle,
);

export const selectBobChatLoading = createSelector(
    selectBobChatState,
    (state) => state.loading,
);

export const selectBobChatMission = createSelector(
    selectBobChatState,
    (state) => state.mission,
);

export const selectBobChatError = createSelector(
    selectBobChatState,
    (state) => state.error,
);
