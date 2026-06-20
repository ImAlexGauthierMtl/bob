import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { catchError, map, mergeMap, of, switchMap, tap, withLatestFrom } from 'rxjs';
import {
    BobArtifact,
    BobChatAction,
    BobChatV1Response,
    BobChatV1Session,
} from '../../shared/models/bob.model';
import { BobAction, BobActionService } from '../../shared/services/bob-action.service';
import { BobService } from '../../shared/services/bob.service';
import { errorMessage } from '../remote-state';
import {
    deleteBobChatSession,
    deleteBobChatSessionFailure,
    deleteBobChatSessionSuccess,
    loadBobChatSessions,
    loadBobChatSessionsFailure,
    loadBobChatSessionsSuccess,
    sendBobChatMessage,
    sendBobChatMessageFailure,
    sendBobChatMessageSuccess,
} from './bob-chat.actions';
import {
    BobChatArtifactView,
    BobChatMessageView,
    BobChatSendSuccessPayload,
    BobChatSessionSummary,
} from './bob-chat.models';
import {
    selectBobChatMission,
    selectBobChatSessionId,
} from './bob-chat.selectors';

@Injectable()
export class BobChatEffects {
    private actions$ = inject(Actions);
    private bobService = inject(BobService);
    private bobActionService = inject(BobActionService);
    private store = inject(Store);

    loadSessions$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadBobChatSessions),
            switchMap(() =>
                this.bobService.listSessionsV1().pipe(
                    map((sessions) => loadBobChatSessionsSuccess({
                        sessions: sessions.map((session) => this.toSessionSummary(session)),
                    })),
                    catchError((error) => of(loadBobChatSessionsFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    sendMessage$ = createEffect(() =>
        this.actions$.pipe(
            ofType(sendBobChatMessage),
            withLatestFrom(
                this.store.select(selectBobChatSessionId),
                this.store.select(selectBobChatMission),
            ),
            mergeMap(([action, sessionId, mission]) =>
                this.bobService.sendMessageV1({
                    message: action.text,
                    session_id: sessionId,
                    channel: action.channel,
                    agent_id: action.agentId,
                    mission: mission.prompt || mission.context
                        ? {
                            prompt: mission.prompt,
                            context: mission.context,
                        }
                        : undefined,
                    client_context: {
                        source: 'cde-angular',
                        channel: action.channel,
                    },
                }).pipe(
                    map((response) => sendBobChatMessageSuccess(this.toSendSuccess(response))),
                    catchError((error) => of(sendBobChatMessageFailure({
                        loadingMessageId: action.loadingMessageId,
                        errorMessageId: this.createMessageId('error'),
                        error: errorMessage(error),
                    }))),
                ),
            ),
        ),
    );

    dispatchBobActions$ = createEffect(
        () =>
            this.actions$.pipe(
                ofType(sendBobChatMessageSuccess),
                tap(({ actions }) => {
                    for (const action of actions) {
                        this.bobActionService.dispatch(action as BobAction);
                    }
                }),
            ),
        { dispatch: false },
    );

    deleteSession$ = createEffect(() =>
        this.actions$.pipe(
            ofType(deleteBobChatSession),
            mergeMap(({ sessionId }) =>
                this.bobService.deleteSession(sessionId).pipe(
                    map(() => deleteBobChatSessionSuccess({ sessionId })),
                    catchError((error) => of(deleteBobChatSessionFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    private toSendSuccess(response: BobChatV1Response): BobChatSendSuccessPayload {
        return {
            responseMessage: this.toAssistantMessage(response),
            sessionId: response.session.id,
            sessionTitle: response.session.title,
            actions: (response.actions || []).filter((action): action is BobAction => this.isKnownBobAction(action)),
        };
    }

    private isKnownBobAction(action: BobChatAction): action is BobAction {
        return [
            'navigate',
            'open_create_dialog',
            'search_entity',
            'change_slide',
            'ui_update_input',
            'ui_select_result',
            'ui_switch_tab',
            'bob_display',
        ].includes(action.type);
    }

    private toAssistantMessage(response: BobChatV1Response): BobChatMessageView {
        return {
            id: response.message.id || this.createMessageId('bob'),
            role: 'bob',
            text: response.message.content,
            time: this.toDate(response.message.created_at),
            toolSteps: response.narration_steps
                ?.filter((step) => step.safe_to_show)
                .map((step) => ({ tool: step.label, status: step.status })),
            artifact: this.toArtifactView(this.firstArtifact(response.artifacts)),
        };
    }

    private toSessionSummary(session: BobChatV1Session): BobChatSessionSummary {
        return {
            id: session.id,
            title: session.title,
            turnCount: session.turn_count,
            createdAt: this.toDate(session.created_at),
            updatedAt: this.toDate(session.updated_at),
        };
    }

    private firstArtifact(artifacts?: BobArtifact[]): BobArtifact | undefined {
        return artifacts && artifacts.length > 0 ? artifacts[0] : undefined;
    }

    private toArtifactView(artifact?: BobArtifact): BobChatArtifactView | undefined {
        if (!artifact) {
            return undefined;
        }

        return {
            type: artifact.type,
            title: artifact.title,
            fields: artifact.fields.map((field) => ({ label: field.label, value: field.value })),
            status: artifact.status,
            entityId: artifact.entityId,
            links: artifact.links?.map((link) => ({ label: link.label, url: link.url, icon: link.icon })),
            columns: artifact.columns ? [...artifact.columns] : undefined,
            rows: artifact.rows?.map((row) => [...row]),
            items: artifact.items?.map((item) => ({ ...item })),
            sections: artifact.sections?.map((section) => ({
                title: section.title,
                subtitle: section.subtitle,
                badge: section.badge,
                items: section.items.map((item) => ({ ...item })),
            })),
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
