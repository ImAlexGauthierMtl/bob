import '@angular/compiler';
import { describe, expect, it } from 'vitest';
import {
    acknowledgeBccInterviewSpeech,
    resetBccInterviewChat,
    sendBccInterviewChatMessage,
    sendBccInterviewChatMessageSuccess,
} from './bcc-interview-chat.actions';
import {
    bccInterviewChatReducer,
    initialBccInterviewChatState,
} from './bcc-interview-chat.reducer';

describe('bccInterviewChatReducer', () => {
    it('keeps the first system-led interview message out of the user transcript', () => {
        const state = bccInterviewChatReducer(initialBccInterviewChatState, sendBccInterviewChatMessage({
            text: '[SYSTEM] Start interview',
            missionPrompt: 'mission',
            orgId: 'org-1',
            orgName: 'Croo',
            showUserMessage: false,
            speakResponse: true,
            messageId: 'user-1',
            loadingMessageId: 'loading-1',
        }));

        expect(state.loading).toBe(true);
        expect(state.messages).toHaveLength(1);
        expect(state.messages[0].role).toBe('bob');
        expect(state.messages[0].isLoading).toBe(true);
    });

    it('stores the Bob response, session and speech cue', () => {
        const loading = bccInterviewChatReducer(initialBccInterviewChatState, sendBccInterviewChatMessage({
            text: 'Bonjour',
            orgId: 'org-1',
            orgName: 'Croo',
            showUserMessage: true,
            speakResponse: true,
            messageId: 'user-1',
            loadingMessageId: 'loading-1',
        }));
        const state = bccInterviewChatReducer(loading, sendBccInterviewChatMessageSuccess({
            responseMessage: {
                id: 'bob-1',
                role: 'bob',
                text: 'Bonjour, je vais guider cette exploration.',
                time: new Date('2026-06-19T12:00:00Z'),
            },
            sessionId: 'session-1',
            speakResponse: true,
        }));

        expect(state.loading).toBe(false);
        expect(state.sessionId).toBe('session-1');
        expect(state.missionSent).toBe(true);
        expect(state.messages.map((message) => message.id)).toEqual(['user-1', 'bob-1']);
        expect(state.pendingSpeech?.text).toContain('guider');

        const acknowledged = bccInterviewChatReducer(state, acknowledgeBccInterviewSpeech({ speechId: 'bob-1' }));
        expect(acknowledged.pendingSpeech).toBeNull();
    });

    it('resets interview chat state', () => {
        const loading = bccInterviewChatReducer(initialBccInterviewChatState, sendBccInterviewChatMessage({
            text: 'Bonjour',
            orgId: 'org-1',
            orgName: 'Croo',
            showUserMessage: true,
            speakResponse: false,
            messageId: 'user-1',
            loadingMessageId: 'loading-1',
        }));

        expect(bccInterviewChatReducer(loading, resetBccInterviewChat())).toEqual(initialBccInterviewChatState);
    });
});
