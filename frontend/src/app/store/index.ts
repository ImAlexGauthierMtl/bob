import { ActionReducerMap } from '@ngrx/store';
import { environment } from '../../environments/environment';
import { authReducer, AuthState } from './auth/auth.reducer';
import { BobAssistantSettingsEffects } from './bob-assistant-settings/bob-assistant-settings.effects';
import { bobAssistantSettingsReducer, BobAssistantSettingsState } from './bob-assistant-settings/bob-assistant-settings.reducer';
import { BobChatEffects } from './bob-chat/bob-chat.effects';
import { bobChatReducer, BobChatState } from './bob-chat/bob-chat.reducer';
import { BobPlatformSettingsEffects } from './bob-platform-settings/bob-platform-settings.effects';
import { bobPlatformSettingsReducer, BobPlatformSettingsState } from './bob-platform-settings/bob-platform-settings.reducer';
import { bobSessionReducer, BobSessionState } from './bob-session/bob-session.reducer';
import { BccInterviewChatEffects } from './bcc-interview-chat/bcc-interview-chat.effects';
import { bccInterviewChatReducer, BccInterviewChatState } from './bcc-interview-chat/bcc-interview-chat.reducer';
import { CommunicationEffects } from './communication/communication.effects';
import { communicationReducer, CommunicationState } from './communication/communication.reducer';
import { CrmEffects } from './crm/crm.effects';
import { crmReducer, CrmState } from './crm/crm.reducer';
import { InboxEffects } from './inbox/inbox.effects';
import { inboxReducer, InboxState } from './inbox/inbox.reducer';
import { KbEffects } from './kb/kb.effects';
import { kbReducer, KbState } from './kb/kb.reducer';
import { PlatformEffects } from './platform/platform.effects';
import { platformReducer, PlatformState } from './platform/platform.reducer';

export interface AppState {
    auth: AuthState;
    crm: CrmState;
    communication: CommunicationState;
    bobSession: BobSessionState;
    bobAssistantSettings: BobAssistantSettingsState;
    bobChat: BobChatState;
    bobPlatformSettings: BobPlatformSettingsState;
    bccInterviewChat: BccInterviewChatState;
    platform: PlatformState;
    kb: KbState;
    inbox: InboxState;
}

export const appReducers: ActionReducerMap<AppState> = {
    auth: authReducer,
    crm: crmReducer,
    communication: communicationReducer,
    bobSession: bobSessionReducer,
    bobAssistantSettings: bobAssistantSettingsReducer,
    bobChat: bobChatReducer,
    bobPlatformSettings: bobPlatformSettingsReducer,
    bccInterviewChat: bccInterviewChatReducer,
    platform: platformReducer,
    kb: kbReducer,
    inbox: inboxReducer,
};

export const appEffects = [
    CrmEffects,
    KbEffects,
    CommunicationEffects,
    PlatformEffects,
    InboxEffects,
    BobAssistantSettingsEffects,
    BobChatEffects,
    BobPlatformSettingsEffects,
    BccInterviewChatEffects,
];

export const storeDevtoolsOptions = {
    maxAge: 25,
    logOnly: environment.production,
};
