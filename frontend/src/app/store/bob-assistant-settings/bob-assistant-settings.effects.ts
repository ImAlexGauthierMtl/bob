import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, forkJoin, map, mergeMap, of, switchMap } from 'rxjs';
import { BobAssistantSettingsService } from '../../shared/services/bob-assistant-settings.service';
import { errorMessage } from '../remote-state';
import {
    loadBobAssistantSettings,
    loadBobAssistantSettingsFailure,
    loadBobAssistantSettingsSuccess,
    saveBobAssistantSettings,
    saveBobAssistantSettingsFailure,
    saveBobAssistantSettingsSuccess,
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
                }).pipe(
                    map(({ conversation, voice }) => loadBobAssistantSettingsSuccess({
                        personality: conversation.personality,
                        voice: voice.voice,
                        availableTones: conversation.available_tones,
                        availableLanguages: conversation.available_languages,
                        availableVoices: voice.available_voices,
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
}
