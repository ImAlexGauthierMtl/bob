import { createAction, props } from '@ngrx/store';
import { SendEmailRequest, ReplyEmailRequest, ForwardEmailRequest } from '../../shared/models/ms365.model';
import { SmartLabel } from '../../shared/models/smart-label.model';
import { UnifiedConnection, UnifiedEmail, UnifiedEmailListResponse } from '../../shared/models/unified-email.model';
import { InboxFilter } from '../../shared/models/inbox-filter.model';

export const loadInboxConnection = createAction('[Inbox] Load connection');
export const loadInboxConnectionSuccess = createAction('[Inbox] Load connection success', props<{ connection: UnifiedConnection | null }>());
export const loadInboxConnectionFailure = createAction('[Inbox] Load connection failure', props<{ error: string }>());

export const loadInboxLabels = createAction('[Inbox] Load labels');
export const loadInboxLabelsSuccess = createAction('[Inbox] Load labels success', props<{ labels: SmartLabel[] }>());
export const loadInboxLabelsFailure = createAction('[Inbox] Load labels failure', props<{ error: string }>());

export const setInboxFilter = createAction('[Inbox] Set filter', props<{ filter: InboxFilter }>());
export const loadInboxEmails = createAction('[Inbox] Load emails', props<{ reset?: boolean }>());
export const loadInboxEmailsSuccess = createAction('[Inbox] Load emails success', props<{ response: UnifiedEmailListResponse; reset: boolean }>());
export const loadInboxEmailsFailure = createAction('[Inbox] Load emails failure', props<{ error: string }>());
export const loadMoreInboxEmails = createAction('[Inbox] Load more emails');

export const selectInboxEmail = createAction('[Inbox] Select email', props<{ email: UnifiedEmail }>());
export const clearInboxSelectedEmail = createAction('[Inbox] Clear selected email');

export const refreshInboxEmails = createAction('[Inbox] Refresh emails');
export const refreshInboxEmailsFailure = createAction('[Inbox] Refresh emails failure', props<{ error: string }>());

export const sendInboxEmail = createAction('[Inbox] Send email', props<{ request: SendEmailRequest }>());
export const sendInboxEmailSuccess = createAction('[Inbox] Send email success');
export const sendInboxEmailFailure = createAction('[Inbox] Send email failure', props<{ error: string }>());

export const replyInboxEmail = createAction('[Inbox] Reply email', props<{ id: string; request: ReplyEmailRequest }>());
export const replyInboxEmailSuccess = createAction('[Inbox] Reply email success');
export const replyInboxEmailFailure = createAction('[Inbox] Reply email failure', props<{ error: string }>());

export const forwardInboxEmail = createAction('[Inbox] Forward email', props<{ id: string; request: ForwardEmailRequest }>());
export const forwardInboxEmailSuccess = createAction('[Inbox] Forward email success');
export const forwardInboxEmailFailure = createAction('[Inbox] Forward email failure', props<{ error: string }>());
