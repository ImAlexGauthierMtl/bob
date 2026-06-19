import { createAction, props } from '@ngrx/store';
import {
    BobConversationPersonality,
    BobLanguageOption,
    BobVoiceOption,
    BobVoiceSettings,
} from '../../shared/services/bob-assistant-settings.service';

export const loadBobAssistantSettings = createAction('[Bob Assistant Settings] Load');
export const loadBobAssistantSettingsSuccess = createAction(
    '[Bob Assistant Settings] Load success',
    props<{
        personality: BobConversationPersonality;
        voice: BobVoiceSettings;
        availableTones: string[];
        availableLanguages: BobLanguageOption[];
        availableVoices: BobVoiceOption[];
    }>(),
);
export const loadBobAssistantSettingsFailure = createAction(
    '[Bob Assistant Settings] Load failure',
    props<{ error: string }>(),
);

export const saveBobAssistantSettings = createAction(
    '[Bob Assistant Settings] Save',
    props<{ personality: BobConversationPersonality; voice: BobVoiceSettings }>(),
);
export const saveBobAssistantSettingsSuccess = createAction(
    '[Bob Assistant Settings] Save success',
    props<{
        personality: BobConversationPersonality;
        voice: BobVoiceSettings;
        availableTones: string[];
        availableLanguages: BobLanguageOption[];
        availableVoices: BobVoiceOption[];
    }>(),
);
export const saveBobAssistantSettingsFailure = createAction(
    '[Bob Assistant Settings] Save failure',
    props<{ error: string }>(),
);
