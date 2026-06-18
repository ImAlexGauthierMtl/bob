import { ActionReducerMap } from '@ngrx/store';
import { environment } from '../../environments/environment';
import { aiAgentReducer, AiAgentState } from './ai-agent/ai-agent.reducer';
import { authReducer, AuthState } from './auth/auth.reducer';
import { CommunicationEffects } from './communication/communication.effects';
import { communicationReducer, CommunicationState } from './communication/communication.reducer';
import { CrmEffects } from './crm/crm.effects';
import { crmReducer, CrmState } from './crm/crm.reducer';
import { KbEffects } from './kb/kb.effects';
import { kbReducer, KbState } from './kb/kb.reducer';
import { PlatformEffects } from './platform/platform.effects';
import { platformReducer, PlatformState } from './platform/platform.reducer';

export interface AppState {
    auth: AuthState;
    crm: CrmState;
    communication: CommunicationState;
    aiAgent: AiAgentState;
    platform: PlatformState;
    kb: KbState;
}

export const appReducers: ActionReducerMap<AppState> = {
    auth: authReducer,
    crm: crmReducer,
    communication: communicationReducer,
    aiAgent: aiAgentReducer,
    platform: platformReducer,
    kb: kbReducer,
};

export const appEffects = [CrmEffects, KbEffects, CommunicationEffects, PlatformEffects];

export const storeDevtoolsOptions = {
    maxAge: 25,
    logOnly: environment.production,
};
