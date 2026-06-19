import { createReducer, on } from '@ngrx/store';
import {
    addBobChatMessage,
    addBobChatToolStep,
    appendBobChatTranscript,
    attachBobChatArtifact,
    deleteBobChatSession,
    deleteBobChatSessionFailure,
    deleteBobChatSessionSuccess,
    loadBobChatSessions,
    loadBobChatSessionsFailure,
    loadBobChatSessionsSuccess,
    selectBobChatSession,
    sendBobChatMessage,
    sendBobChatMessageFailure,
    sendBobChatMessageSuccess,
    setBobChatMission,
    startNewBobChatConversation,
} from './bob-chat.actions';
import { BobChatMessageView, BobChatMissionState, BobChatSessionSummary } from './bob-chat.models';

const WELCOME_MESSAGE: BobChatMessageView = {
    id: 'bob-welcome',
    role: 'bob',
    text: 'Hello! I\'m Bob, your AI assistant. How can I help you today?',
    time: new Date(0),
};

export interface BobChatState {
    messages: BobChatMessageView[];
    sessions: BobChatSessionSummary[];
    sessionId: string | null;
    activeTitle: string;
    loading: boolean;
    sessionsLoading: boolean;
    deletingSessionId: string | null;
    error: string | null;
    mission: BobChatMissionState;
}

export const initialBobChatState: BobChatState = {
    messages: [WELCOME_MESSAGE],
    sessions: [],
    sessionId: null,
    activeTitle: 'New Conversation',
    loading: false,
    sessionsLoading: false,
    deletingSessionId: null,
    error: null,
    mission: { active: false },
};

export const bobChatReducer = createReducer(
    initialBobChatState,
    on(loadBobChatSessions, (state) => ({ ...state, sessionsLoading: true, error: null })),
    on(loadBobChatSessionsSuccess, (state, { sessions }) => ({
        ...state,
        sessions,
        sessionsLoading: false,
        error: null,
    })),
    on(loadBobChatSessionsFailure, (state, { error }) => ({
        ...state,
        sessionsLoading: false,
        error,
    })),
    on(sendBobChatMessage, (state, { messageId, loadingMessageId, text }) => ({
        ...state,
        loading: true,
        error: null,
        messages: [
            ...state.messages,
            {
                id: messageId,
                role: 'user',
                text,
                time: new Date(),
            },
            {
                id: loadingMessageId,
                role: 'bob',
                text: '',
                time: new Date(),
                isLoading: true,
            },
        ],
    })),
    on(sendBobChatMessageSuccess, (state, { responseMessage, sessionId, sessionTitle }) => ({
        ...state,
        messages: [...state.messages.filter((message) => !message.isLoading), responseMessage],
        sessionId,
        activeTitle: sessionTitle || state.activeTitle,
        loading: false,
        error: null,
        mission: {
            ...state.mission,
            prompt: undefined,
        },
    })),
    on(sendBobChatMessageFailure, (state, { loadingMessageId, errorMessageId, error }) => ({
        ...state,
        messages: [
            ...state.messages.filter((message) => message.id !== loadingMessageId),
            {
                id: errorMessageId,
                role: 'bob',
                text: 'Sorry, I encountered an error. Please try again.',
                time: new Date(),
            },
        ],
        loading: false,
        error,
    })),
    on(selectBobChatSession, (state, { sessionId, title }) => ({
        ...state,
        sessionId,
        activeTitle: title || `Session #${sessionId.slice(0, 8)}`,
        messages: [
            {
                id: `resume-${sessionId}`,
                role: 'bob',
                text: 'Resuming conversation...',
                time: new Date(),
            },
        ],
    })),
    on(deleteBobChatSession, (state, { sessionId }) => ({
        ...state,
        deletingSessionId: sessionId,
        error: null,
    })),
    on(deleteBobChatSessionSuccess, (state, { sessionId }) => ({
        ...state,
        deletingSessionId: null,
        sessions: state.sessions.filter((session) => session.id !== sessionId),
        ...(state.sessionId === sessionId
            ? {
                sessionId: null,
                activeTitle: 'New Conversation',
                messages: [welcomeMessage()],
            }
            : {}),
    })),
    on(deleteBobChatSessionFailure, (state, { error }) => ({
        ...state,
        deletingSessionId: null,
        error,
    })),
    on(startNewBobChatConversation, (state) => ({
        ...state,
        sessionId: null,
        activeTitle: 'New Conversation',
        messages: [welcomeMessage()],
        loading: false,
        error: null,
        mission: { active: false },
    })),
    on(setBobChatMission, (state, { prompt, context, active }) => ({
        ...state,
        mission: { prompt, context, active },
    })),
    on(addBobChatMessage, (state, { message }) => ({
        ...state,
        messages: [...state.messages, message],
    })),
    on(appendBobChatTranscript, (state, { messageId, text }) => ({
        ...state,
        messages: state.messages.map((message) =>
            message.id === messageId
                ? { ...message, text: `${message.text}${text}` }
                : message,
        ),
    })),
    on(addBobChatToolStep, (state, { messageId, step }) => ({
        ...state,
        messages: addToolStep(state.messages, messageId, step),
    })),
    on(attachBobChatArtifact, (state, { messageId, artifact }) => ({
        ...state,
        messages: state.messages.map((message) =>
            message.id === messageId ? { ...message, artifact } : message,
        ),
    })),
);

function welcomeMessage(): BobChatMessageView {
    return {
        ...WELCOME_MESSAGE,
        time: new Date(),
    };
}

function addToolStep(
    messages: BobChatMessageView[],
    messageId: string | undefined,
    step: { tool: string; status: string },
): BobChatMessageView[] {
    const targetIndex = messageId
        ? messages.findIndex((message) => message.id === messageId)
        : findLastBobMessageIndex(messages);

    if (targetIndex < 0) {
        return messages;
    }

    return messages.map((message, index) =>
        index === targetIndex
            ? { ...message, toolSteps: [...(message.toolSteps || []), step] }
            : message,
    );
}

function findLastBobMessageIndex(messages: BobChatMessageView[]): number {
    for (let index = messages.length - 1; index >= 0; index--) {
        if (messages[index].role === 'bob') {
            return index;
        }
    }
    return -1;
}
