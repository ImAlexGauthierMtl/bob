import '@angular/compiler';
import { describe, expect, it } from 'vitest';
import { sendBccInterviewChatMessage } from './bcc-interview-chat.actions';
import { buildBccInterviewBobChatRequest } from './bcc-interview-chat.effects';

function sendAction(overrides: Partial<ReturnType<typeof sendBccInterviewChatMessage>> = {}) {
    return sendBccInterviewChatMessage({
        text: '[SYSTEM] Start',
        missionPrompt: 'Mission prompt',
        orgId: 'org-1',
        orgName: 'Croo Local',
        showUserMessage: false,
        speakResponse: false,
        messageId: 'user-1',
        loadingMessageId: 'loading-1',
        ...overrides,
    });
}

describe('buildBccInterviewBobChatRequest', () => {
    it('sends the first interview message with BCC mission and client context', () => {
        const request = buildBccInterviewBobChatRequest(sendAction(), undefined, false);

        expect(request.message).toBe('[SYSTEM] Start');
        expect(request.session_id).toBeUndefined();
        expect(request.channel).toBe('workspace');
        expect(request.mission?.prompt).toBe('Mission prompt');
        expect(request.mission?.context).toEqual({
            surface: 'bcc-interview',
            organization_id: 'org-1',
            organization_name: 'Croo Local',
        });
        expect(request.client_context).toEqual({
            source: 'cde-angular',
            surface: 'bcc-interview',
            organization_id: 'org-1',
            channel: 'workspace',
        });
    });

    it('does not resend mission once the interview session exists', () => {
        const request = buildBccInterviewBobChatRequest(
            sendAction({ text: 'Ma réponse', showUserMessage: true, speakResponse: true }),
            'session-bcc-1',
            true,
        );

        expect(request.message).toBe('Ma réponse');
        expect(request.session_id).toBe('session-bcc-1');
        expect(request.channel).toBe('voice_app');
        expect(request.mission).toBeUndefined();
        expect(request.client_context).toEqual({
            source: 'cde-angular',
            surface: 'bcc-interview',
            organization_id: 'org-1',
            channel: 'voice_app',
        });
    });
});
