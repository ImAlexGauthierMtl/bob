import { createAction, props } from '@ngrx/store';
import { BccInterviewChatMessage } from './bcc-interview-chat.models';

export const resetBccInterviewChat = createAction('[BCC Interview Chat] Reset');

export const sendBccInterviewChatMessage = createAction(
    '[BCC Interview Chat] Send message',
    props<{
        text: string;
        missionPrompt?: string;
        orgId: string;
        orgName: string;
        showUserMessage: boolean;
        speakResponse: boolean;
        messageId: string;
        loadingMessageId: string;
    }>(),
);

export const sendBccInterviewChatMessageSuccess = createAction(
    '[BCC Interview Chat] Send message success',
    props<{
        responseMessage: BccInterviewChatMessage;
        sessionId: string;
        speakResponse: boolean;
    }>(),
);

export const sendBccInterviewChatMessageFailure = createAction(
    '[BCC Interview Chat] Send message failure',
    props<{ loadingMessageId: string; errorMessageId: string; error: string }>(),
);

export const acknowledgeBccInterviewSpeech = createAction(
    '[BCC Interview Chat] Acknowledge speech',
    props<{ speechId: string }>(),
);
