import '@angular/compiler';
import { createEnvironmentInjector, EnvironmentInjector, runInInjectionContext } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Actions } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { Subject, of } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';

import { BobActionService } from '../../shared/services/bob-action.service';
import { BobService } from '../../shared/services/bob.service';
import { sendBobChatMessage, sendBobChatMessageSuccess } from './bob-chat.actions';
import { BobChatEffects } from './bob-chat.effects';
import { selectBobChatMission, selectBobChatSessionId } from './bob-chat.selectors';

describe('BobChatEffects', () => {
    it('sends the selected runtime agent id through the Bob Chat B4F contract', async () => {
        const actions$ = new Subject<ReturnType<typeof sendBobChatMessage>>();
        const bobService = {
            sendMessageV1: vi.fn().mockReturnValue(of({
                message: {
                    id: 'assistant-1',
                    role: 'assistant',
                    content: 'Bonjour',
                    created_at: '2026-06-20T05:00:00Z',
                },
                session: {
                    id: 'chat-1',
                    title: 'Runtime proof',
                    channel: 'workspace',
                    turn_count: 1,
                    created_at: '2026-06-20T05:00:00Z',
                    updated_at: '2026-06-20T05:00:00Z',
                },
                run: {
                    id: 'run-1',
                    status: 'completed',
                    mode: 'provider_fireworks',
                },
                actions: [],
                narration_steps: [],
                artifacts: [],
            })),
        };
        const store = {
            select: vi.fn((selector) => {
                if (selector === selectBobChatSessionId) return of('chat-existing');
                if (selector === selectBobChatMission) return of({ active: false });
                return of(undefined);
            }),
        };

        const injector = createEnvironmentInjector([
                { provide: Actions, useValue: new Actions(actions$) },
                { provide: BobService, useValue: bobService },
                { provide: BobActionService, useValue: { dispatch: vi.fn() } },
                { provide: Store, useValue: store },
        ], TestBed.inject(EnvironmentInjector));

        const effects = runInInjectionContext(injector, () => new BobChatEffects());
        const result = new Promise((resolve) => {
            effects.sendMessage$.subscribe(resolve);
        });

        actions$.next(sendBobChatMessage({
            messageId: 'user-1',
            loadingMessageId: 'loading-1',
            text: 'Salut Bob',
            channel: 'workspace',
            agentId: 'agent-cde-proof',
        }));

        expect(await result).toEqual(expect.objectContaining(sendBobChatMessageSuccess({
            responseMessage: expect.objectContaining({
                id: 'assistant-1',
                role: 'bob',
                text: 'Bonjour',
            }),
            sessionId: 'chat-1',
            sessionTitle: 'Runtime proof',
            actions: [],
        })));
        expect(bobService.sendMessageV1).toHaveBeenCalledWith(expect.objectContaining({
            message: 'Salut Bob',
            session_id: 'chat-existing',
            channel: 'workspace',
            agent_id: 'agent-cde-proof',
        }));
        injector.destroy();
    });
});
