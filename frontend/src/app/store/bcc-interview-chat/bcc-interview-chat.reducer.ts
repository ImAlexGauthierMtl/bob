import { createReducer, on } from '@ngrx/store';
import {
    acknowledgeBccInterviewSpeech,
    resetBccInterviewChat,
    sendBccInterviewChatMessage,
    sendBccInterviewChatMessageFailure,
    sendBccInterviewChatMessageSuccess,
} from './bcc-interview-chat.actions';
import { BccInterviewChatMessage, BccInterviewSpeechCue } from './bcc-interview-chat.models';

export interface BccInterviewChatState {
    messages: BccInterviewChatMessage[];
    sessionId: string | null;
    missionSent: boolean;
    loading: boolean;
    error: string | null;
    pendingSpeech: BccInterviewSpeechCue | null;
}

export const initialBccInterviewChatState: BccInterviewChatState = {
    messages: [],
    sessionId: null,
    missionSent: false,
    loading: false,
    error: null,
    pendingSpeech: null,
};

export const bccInterviewChatReducer = createReducer(
    initialBccInterviewChatState,
    on(resetBccInterviewChat, () => initialBccInterviewChatState),
    on(sendBccInterviewChatMessage, (state, { text, showUserMessage, messageId, loadingMessageId }) => ({
        ...state,
        loading: true,
        error: null,
        messages: [
            ...state.messages,
            ...(showUserMessage
                ? [{
                    id: messageId,
                    role: 'user' as const,
                    text,
                    time: new Date(),
                }]
                : []),
            {
                id: loadingMessageId,
                role: 'bob' as const,
                text: '',
                time: new Date(),
                isLoading: true,
            },
        ],
    })),
    on(sendBccInterviewChatMessageSuccess, (state, { responseMessage, sessionId, speakResponse }) => ({
        ...state,
        messages: [...state.messages.filter((message) => !message.isLoading), responseMessage],
        sessionId,
        missionSent: true,
        loading: false,
        error: null,
        pendingSpeech: speakResponse ? { id: responseMessage.id, text: responseMessage.text } : state.pendingSpeech,
    })),
    on(sendBccInterviewChatMessageFailure, (state, { loadingMessageId, errorMessageId, error }) => ({
        ...state,
        messages: [
            ...state.messages.filter((message) => message.id !== loadingMessageId),
            {
                id: errorMessageId,
                role: 'bob',
                text: 'Erreur de communication. Réessayez.',
                time: new Date(),
            },
        ],
        loading: false,
        error,
    })),
    on(acknowledgeBccInterviewSpeech, (state, { speechId }) => ({
        ...state,
        pendingSpeech: state.pendingSpeech?.id === speechId ? null : state.pendingSpeech,
    })),
);
