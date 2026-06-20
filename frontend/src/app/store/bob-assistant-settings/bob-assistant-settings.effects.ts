import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, forkJoin, map, mergeMap, of, switchMap } from 'rxjs';
import { BobAssistantSettingsService } from '../../shared/services/bob-assistant-settings.service';
import { errorMessage } from '../remote-state';
import {
    createBobRuntimeAgent,
    createBobRuntimeSkill,
    createBobRuntimeTool,
    loadBobAssistantSettings,
    loadBobAssistantSettingsFailure,
    loadBobAssistantSettingsSuccess,
    saveBobAssistantSettings,
    saveBobAssistantSettingsFailure,
    saveBobAssistantSettingsSuccess,
    updateBobRuntimeSettingsFailure,
    updateBobRuntimeSettingsSuccess,
} from './bob-assistant-settings.actions';

@Injectable()
export class BobAssistantSettingsEffects {
    private actions$ = inject(Actions);
    private service = inject(BobAssistantSettingsService);

    load$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadBobAssistantSettings),
            switchMap(() =>
                forkJoin({
                    conversation: this.service.getConversation(),
                    voice: this.service.getVoice(),
                    runtime: this.service.getRuntime(),
                    memorySettings: this.service.getMemory().pipe(
                        catchError((error) => of({
                            status: null,
                            vector_index: {
                                config: null,
                                health: null,
                                degraded: [{
                                    target: 'memory_settings',
                                    status_code: 0,
                                    detail: { code: errorMessage(error) },
                                }],
                            },
                            rag: null,
                            source: 'frontend-degraded',
                        })),
                    ),
                }).pipe(
                    map(({ conversation, voice, runtime, memorySettings }) => loadBobAssistantSettingsSuccess({
                        personality: conversation.personality,
                        voice: voice.voice,
                        availableTones: conversation.available_tones,
                        availableLanguages: conversation.available_languages,
                        availableVoices: voice.available_voices,
                        runtime,
                        memorySettings,
                    })),
                    catchError((error) => of(loadBobAssistantSettingsFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    save$ = createEffect(() =>
        this.actions$.pipe(
            ofType(saveBobAssistantSettings),
            mergeMap(({ personality, voice }) =>
                forkJoin({
                    conversation: this.service.updateConversation(personality),
                    voiceSettings: this.service.updateVoice(voice),
                }).pipe(
                    map(({ conversation, voiceSettings }) => saveBobAssistantSettingsSuccess({
                        personality: conversation.personality,
                        voice: voiceSettings.voice,
                        availableTones: conversation.available_tones,
                        availableLanguages: conversation.available_languages,
                        availableVoices: voiceSettings.available_voices,
                    })),
                    catchError((error) => of(saveBobAssistantSettingsFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    createRuntimeAgent$ = createEffect(() =>
        this.actions$.pipe(
            ofType(createBobRuntimeAgent),
            mergeMap(({ agent }) =>
                this.service.createRuntimeAgent(agent).pipe(
                    map(({ runtime }) => updateBobRuntimeSettingsSuccess({
                        runtime,
                        notice: 'Agent added',
                    })),
                    catchError((error) => of(updateBobRuntimeSettingsFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    createRuntimeSkill$ = createEffect(() =>
        this.actions$.pipe(
            ofType(createBobRuntimeSkill),
            mergeMap(({ skill }) =>
                this.service.createRuntimeSkill(skill).pipe(
                    map(({ runtime }) => updateBobRuntimeSettingsSuccess({
                        runtime,
                        notice: 'Skill added',
                    })),
                    catchError((error) => of(updateBobRuntimeSettingsFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    createRuntimeTool$ = createEffect(() =>
        this.actions$.pipe(
            ofType(createBobRuntimeTool),
            mergeMap(({ tool }) =>
                this.service.createRuntimeTool(tool).pipe(
                    map(({ runtime }) => updateBobRuntimeSettingsSuccess({
                        runtime,
                        notice: 'Tool added',
                    })),
                    catchError((error) => of(updateBobRuntimeSettingsFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );
}
