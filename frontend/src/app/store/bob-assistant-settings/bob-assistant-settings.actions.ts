import { createAction, props } from '@ngrx/store';
import {
    BobMemorySettingsResponse,
    BobRuntimeAgent,
    BobRuntimeSettingsResponse,
    BobRuntimeSkill,
    BobRuntimeTool,
} from '../../shared/services/bob-assistant-settings.service';

export const loadBobAssistantSettings = createAction('[Bob Assistant Settings] Load');
export const loadBobAssistantSettingsSuccess = createAction(
    '[Bob Assistant Settings] Load success',
    props<{
        runtime: BobRuntimeSettingsResponse;
        memorySettings: BobMemorySettingsResponse;
    }>(),
);
export const loadBobAssistantSettingsFailure = createAction(
    '[Bob Assistant Settings] Load failure',
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
