import { createAction, props } from '@ngrx/store';
import {
    BobChatArtifactView,
    BobChatConfirmationStatus,
    BobChatMessageView,
    BobChatSendRequest,
    BobChatSendSuccessPayload,
    BobChatSessionSummary,
    BobChatToolStep,
} from './bob-chat.models';

export const loadBobChatSessions = createAction('[Bob Chat] Load sessions');
export const loadBobChatSessionsSuccess = createAction(
    '[Bob Chat] Load sessions success',
    props<{ sessions: BobChatSessionSummary[] }>(),
);
export const loadBobChatSessionsFailure = createAction(
    '[Bob Chat] Load sessions failure',
    props<{ error: string }>(),
);

export const sendBobChatMessage = createAction(
    '[Bob Chat] Send message',
    props<BobChatSendRequest>(),
);
export const sendBobChatMessageSuccess = createAction(
    '[Bob Chat] Send message success',
    props<BobChatSendSuccessPayload>(),
);
export const sendBobChatMessageFailure = createAction(
    '[Bob Chat] Send message failure',
    props<{ loadingMessageId: string; errorMessageId: string; error: string }>(),
);

export const selectBobChatSession = createAction(
    '[Bob Chat] Select session',
    props<{ sessionId: string; title: string }>(),
);
export const deleteBobChatSession = createAction(
    '[Bob Chat] Delete session',
    props<{ sessionId: string }>(),
);
export const deleteBobChatSessionSuccess = createAction(
    '[Bob Chat] Delete session success',
    props<{ sessionId: string }>(),
);
export const deleteBobChatSessionFailure = createAction(
    '[Bob Chat] Delete session failure',
    props<{ error: string }>(),
);

export const startNewBobChatConversation = createAction('[Bob Chat] Start new conversation');
export const setBobChatMission = createAction(
    '[Bob Chat] Set mission',
    props<{ prompt?: string; context?: Record<string, unknown>; active: boolean }>(),
);

export const addBobChatMessage = createAction(
    '[Bob Chat] Add message',
    props<{ message: BobChatMessageView }>(),
);
export const appendBobChatTranscript = createAction(
    '[Bob Chat] Append transcript',
    props<{ messageId: string; text: string }>(),
);
export const addBobChatToolStep = createAction(
    '[Bob Chat] Add tool step',
    props<{ messageId?: string; step: BobChatToolStep }>(),
);
export const attachBobChatArtifact = createAction(
    '[Bob Chat] Attach artifact',
    props<{ messageId: string; artifact: BobChatArtifactView }>(),
);

export const confirmBobChatAction = createAction(
    '[Bob Chat] Confirm action',
    props<{ messageId: string; runId: string; confirmationId: string }>(),
);
export const cancelBobChatAction = createAction(
    '[Bob Chat] Cancel action',
    props<{ messageId: string; runId: string; confirmationId: string }>(),
);
export const resolveBobChatActionSuccess = createAction(
    '[Bob Chat] Resolve action success',
    props<{
        messageId: string;
        confirmationId: string;
        status: BobChatConfirmationStatus;
        executionStatus?: string;
        executionLabel?: string;
    }>(),
);
export const resolveBobChatActionFailure = createAction(
    '[Bob Chat] Resolve action failure',
    props<{ messageId: string; confirmationId: string; error: string }>(),
);
