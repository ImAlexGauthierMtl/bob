import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { catchError, concatMap, map, of, switchMap, take } from 'rxjs';
import { BobChatRequest, BobChatV1Response } from '../../shared/models/bob.model';
import { BobService } from '../../shared/services/bob.service';
import { errorMessage } from '../remote-state';
import {
    sendBccInterviewChatMessage,
    sendBccInterviewChatMessageFailure,
    sendBccInterviewChatMessageSuccess,
} from './bcc-interview-chat.actions';
import { BccInterviewChatMessage } from './bcc-interview-chat.models';
import {
    selectBccInterviewChatMissionSent,
    selectBccInterviewChatSessionId,
} from './bcc-interview-chat.selectors';

export function buildBccInterviewBobChatRequest(
    action: ReturnType<typeof sendBccInterviewChatMessage>,
    sessionId: string | undefined,
    missionSent: boolean,
): BobChatRequest {
    const channel = action.speakResponse ? 'voice_app' : 'workspace';

    return {
        message: action.text,
        session_id: sessionId,
        channel,
        mission: !missionSent && action.missionPrompt
            ? {
                prompt: action.missionPrompt,
                context: {
                    surface: 'bcc-interview',
                    organization_id: action.orgId,
                    organization_name: action.orgName,
                },
            }
            : undefined,
        client_context: {
            source: 'cde-angular',
            surface: 'bcc-interview',
            organization_id: action.orgId,
            channel,
        },
    };
}

@Injectable()
export class BccInterviewChatEffects {
    private actions$ = inject(Actions);
    private bobService = inject(BobService);
    private store = inject(Store);

    sendMessage$ = createEffect(() =>
        this.actions$.pipe(
            ofType(sendBccInterviewChatMessage),
            concatMap((action) =>
                this.store.select(selectBccInterviewChatSessionId).pipe(
                    take(1),
                    switchMap((sessionId) =>
                        this.store.select(selectBccInterviewChatMissionSent).pipe(
                            take(1),
                            switchMap((missionSent) =>
                                this.bobService.sendMessageV1(
                                    buildBccInterviewBobChatRequest(action, sessionId, missionSent),
                                ).pipe(
                                    map((response) => sendBccInterviewChatMessageSuccess({
                                        responseMessage: this.toAssistantMessage(response),
                                        sessionId: response.session.id,
                                        speakResponse: action.speakResponse,
                                    })),
                                    catchError((error) => of(sendBccInterviewChatMessageFailure({
                                        loadingMessageId: action.loadingMessageId,
                                        errorMessageId: this.createMessageId('bcc-error'),
                                        error: errorMessage(error),
                                    }))),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    );

    private toAssistantMessage(response: BobChatV1Response): BccInterviewChatMessage {
        return {
            id: response.message.id || this.createMessageId('bcc-bob'),
            role: 'bob',
            text: response.message.content,
            time: this.toDate(response.message.created_at),
        };
    }

    private toDate(value: string): Date {
        const parsed = Date.parse(value);
        return Number.isFinite(parsed) ? new Date(parsed) : new Date();
    }

    private createMessageId(prefix: string): string {
        if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
            return `${prefix}-${crypto.randomUUID()}`;
        }

        return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }
}
