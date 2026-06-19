import { createFeatureSelector, createSelector } from '@ngrx/store';
import { InboxState } from './inbox.reducer';

export const selectInboxState = createFeatureSelector<InboxState>('inbox');

export const selectInboxEmails = createSelector(selectInboxState, (state) => state.emails);
export const selectInboxSelectedEmail = createSelector(selectInboxState, (state) => state.selectedEmail);
export const selectInboxFilter = createSelector(selectInboxState, (state) => state.filter);
export const selectInboxLabels = createSelector(selectInboxState, (state) => state.labels);
export const selectInboxTotal = createSelector(selectInboxState, (state) => state.total);
export const selectInboxSkip = createSelector(selectInboxState, (state) => state.skip);
export const selectInboxLimit = createSelector(selectInboxState, (state) => state.limit);
export const selectInboxHasMore = createSelector(
    selectInboxEmails,
    selectInboxTotal,
    (emails, total) => emails.length < total,
);
export const selectInboxLoadingEmails = createSelector(selectInboxState, (state) => state.loadingEmails);
export const selectInboxSending = createSelector(selectInboxState, (state) => state.sending);
export const selectInboxReplying = createSelector(selectInboxState, (state) => state.replying);
export const selectInboxForwarding = createSelector(selectInboxState, (state) => state.forwarding);
export const selectInboxSendError = createSelector(selectInboxState, (state) => state.sendError);
export const selectInboxReplyError = createSelector(selectInboxState, (state) => state.replyError);
export const selectInboxForwardError = createSelector(selectInboxState, (state) => state.forwardError);
export const selectInboxConnection = createSelector(selectInboxState, (state) => state.connection);
export const selectInboxConnectionChecked = createSelector(selectInboxState, (state) => state.connectionChecked);

export const selectInboxRangeText = createSelector(
    selectInboxEmails,
    selectInboxSkip,
    (emails, skip) => `${emails.length > 0 ? skip + 1 : 0}-${skip + emails.length}`,
);

export const selectInboxShowConnectionBanner = createSelector(
    selectInboxConnection,
    selectInboxConnectionChecked,
    (connection, checked) => {
        if (!checked) return false;
        if (!connection) return true;
        return !connection.isActive
            || connection.status === 'token_expired'
            || connection.status === 'needs_reauth';
    },
);

export const selectInboxConnectionBannerMessage = createSelector(
    selectInboxConnection,
    (connection) => connection
        ? 'Your email connection needs to be refreshed. Go to Settings > Integrations.'
        : 'Connect your email account via Settings > Integrations to sync your emails.',
);
