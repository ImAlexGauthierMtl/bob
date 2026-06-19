import '@angular/compiler';
import { describe, expect, it } from 'vitest';
import {
    addBobChatToolStep,
    sendBobChatMessage,
    sendBobChatMessageSuccess,
    startNewBobChatConversation,
} from './bob-chat.actions';
import { bobChatReducer, initialBobChatState } from './bob-chat.reducer';

describe('bobChatReducer', () => {
    it('adds user and loading messages when sending', () => {
        const state = bobChatReducer(initialBobChatState, sendBobChatMessage({
            messageId: 'user-1',
            loadingMessageId: 'loading-1',
            text: 'Hello',
            channel: 'compact',
        }));

        expect(state.loading).toBe(true);
        expect(state.messages.at(-2)?.text).toBe('Hello');
        expect(state.messages.at(-1)?.isLoading).toBe(true);
    });

    it('stores the v1 assistant response without legacy response shape', () => {
        const sending = bobChatReducer(initialBobChatState, sendBobChatMessage({
            messageId: 'user-1',
            loadingMessageId: 'loading-1',
            text: 'Hello',
            channel: 'compact',
        }));

        const state = bobChatReducer(sending, sendBobChatMessageSuccess({
            responseMessage: {
                id: 'assistant-1',
                role: 'bob',
                text: 'Bonjour',
                time: new Date('2026-06-19T12:00:00Z'),
                toolSteps: [{ tool: 'Recherche CRM', status: 'complete' }],
            },
            sessionId: 'session-1',
            sessionTitle: 'CRM help',
            actions: [],
        }));

        expect(state.loading).toBe(false);
        expect(state.sessionId).toBe('session-1');
        expect(state.activeTitle).toBe('CRM help');
        expect(state.messages.some((message) => message.isLoading)).toBe(false);
        expect(state.messages.at(-1)?.toolSteps?.[0].tool).toBe('Recherche CRM');
    });

    it('keeps voice tool badges in the same store path', () => {
        const withBadge = bobChatReducer(initialBobChatState, addBobChatToolStep({
            step: { tool: 'navigate_to', status: 'ok' },
        }));

        expect(withBadge.messages.at(-1)?.toolSteps?.[0].tool).toBe('navigate_to');
    });

    it('resets the active conversation', () => {
        const state = bobChatReducer({
            ...initialBobChatState,
            sessionId: 'session-1',
            activeTitle: 'Existing',
            messages: [
                { id: 'm1', role: 'user', text: 'Existing', time: new Date() },
            ],
        }, startNewBobChatConversation());

        expect(state.sessionId).toBeNull();
        expect(state.activeTitle).toBe('New Conversation');
        expect(state.messages[0].role).toBe('bob');
    });
});
