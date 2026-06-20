import { createAction, props } from '@ngrx/store';
import {
    BobConversationPersonality,
    BobLanguageOption,
    BobMemorySettingsResponse,
    BobRuntimeAgent,
    BobRuntimeSettingsResponse,
    BobRuntimeSkill,
    BobRuntimeTool,
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
        runtime: BobRuntimeSettingsResponse;
        memorySettings: BobMemorySettingsResponse;
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

export const createBobRuntimeAgent = createAction(
    '[Bob Assistant Settings] Create runtime agent',
    props<{ agent: Partial<BobRuntimeAgent> & { name: string } }>(),
);
export const createBobRuntimeSkill = createAction(
    '[Bob Assistant Settings] Create runtime skill',
    props<{ skill: Partial<BobRuntimeSkill> & { name: string } }>(),
);
export const createBobRuntimeTool = createAction(
    '[Bob Assistant Settings] Create runtime tool',
    props<{ tool: Partial<BobRuntimeTool> & { name: string } }>(),
);
export const updateBobRuntimeSettingsSuccess = createAction(
    '[Bob Assistant Settings] Update runtime success',
    props<{ runtime: BobRuntimeSettingsResponse; notice: string }>(),
);
export const updateBobRuntimeSettingsFailure = createAction(
    '[Bob Assistant Settings] Update runtime failure',
    props<{ error: string }>(),
);
