import { createReducer, on } from '@ngrx/store';
import { InboxFilter } from '../../shared/models/inbox-filter.model';
import { SmartLabel } from '../../shared/models/smart-label.model';
import { UnifiedConnection, UnifiedEmail } from '../../shared/models/unified-email.model';
import {
    clearInboxSelectedEmail,
    forwardInboxEmail,
    forwardInboxEmailFailure,
    forwardInboxEmailSuccess,
    loadInboxConnection,
    loadInboxConnectionFailure,
    loadInboxConnectionSuccess,
    loadInboxEmails,
    loadInboxEmailsFailure,
    loadInboxEmailsSuccess,
    loadInboxLabels,
    loadInboxLabelsFailure,
    loadInboxLabelsSuccess,
    loadMoreInboxEmails,
    refreshInboxEmails,
    replyInboxEmail,
    replyInboxEmailFailure,
    replyInboxEmailSuccess,
    selectInboxEmail,
    sendInboxEmail,
    sendInboxEmailFailure,
    sendInboxEmailSuccess,
    setInboxFilter,
} from './inbox.actions';

export interface InboxState {
    emails: UnifiedEmail[];
    selectedEmail: UnifiedEmail | null;
    filter: InboxFilter;
    connection: UnifiedConnection | null;
    connectionChecked: boolean;
    labels: SmartLabel[];
    loadingEmails: boolean;
    loadingLabels: boolean;
    loadingConnection: boolean;
    syncing: boolean;
    sending: boolean;
    replying: boolean;
    forwarding: boolean;
    error: string | null;
    sendError: string | null;
    replyError: string | null;
    forwardError: string | null;
    labelsError: string | null;
    total: number;
    skip: number;
    limit: number;
}

export const initialInboxState: InboxState = {
    emails: [],
    selectedEmail: null,
    filter: {},
    connection: null,
    connectionChecked: false,
    labels: [],
    loadingEmails: false,
    loadingLabels: false,
    loadingConnection: false,
    syncing: false,
    sending: false,
    replying: false,
    forwarding: false,
    error: null,
    sendError: null,
    replyError: null,
    forwardError: null,
    labelsError: null,
    total: 0,
    skip: 0,
    limit: 50,
};

export const inboxReducer = createReducer(
    initialInboxState,
    on(loadInboxConnection, (state) => ({
        ...state,
        loadingConnection: true,
    })),
    on(loadInboxConnectionSuccess, (state, { connection }) => ({
        ...state,
        connection,
        connectionChecked: true,
        loadingConnection: false,
    })),
    on(loadInboxConnectionFailure, (state) => ({
        ...state,
        connection: null,
        connectionChecked: true,
        loadingConnection: false,
    })),
    on(loadInboxLabels, (state) => ({
        ...state,
        loadingLabels: true,
        labelsError: null,
    })),
    on(loadInboxLabelsSuccess, (state, { labels }) => ({
        ...state,
        labels,
        loadingLabels: false,
    })),
    on(loadInboxLabelsFailure, (state, { error }) => ({
        ...state,
        loadingLabels: false,
        labelsError: error,
    })),
    on(setInboxFilter, (state, { filter }) => ({
        ...state,
        filter,
        emails: [],
        selectedEmail: null,
        skip: 0,
        total: 0,
    })),
    on(loadInboxEmails, (state, { reset }) => ({
        ...state,
        loadingEmails: true,
        error: null,
        skip: reset ? 0 : state.skip,
        emails: reset ? [] : state.emails,
    })),
    on(loadMoreInboxEmails, (state) => ({
        ...state,
        loadingEmails: state.emails.length < state.total,
        error: null,
        skip: state.emails.length < state.total ? state.skip + state.limit : state.skip,
    })),
    on(loadInboxEmailsSuccess, (state, { response, reset }) => ({
        ...state,
        emails: reset ? response.items : [...state.emails, ...response.items],
        total: response.total,
        skip: response.skip,
        limit: response.limit,
        loadingEmails: false,
        syncing: false,
    })),
    on(loadInboxEmailsFailure, (state, { error }) => ({
        ...state,
        loadingEmails: false,
        syncing: false,
        error,
    })),
    on(selectInboxEmail, (state, { email }) => {
        const selectedEmail = { ...email, is_read: true };
        return {
            ...state,
            selectedEmail,
            emails: state.emails.map((item) => item.id === email.id ? selectedEmail : item),
        };
    }),
    on(clearInboxSelectedEmail, (state) => ({
        ...state,
        selectedEmail: null,
    })),
    on(refreshInboxEmails, (state) => ({
        ...state,
        syncing: true,
        error: null,
    })),
    on(sendInboxEmail, (state) => ({
        ...state,
        sending: true,
        sendError: null,
    })),
    on(sendInboxEmailSuccess, (state) => ({
        ...state,
        sending: false,
    })),
    on(sendInboxEmailFailure, (state, { error }) => ({
        ...state,
        sending: false,
        sendError: error,
    })),
    on(replyInboxEmail, (state) => ({
        ...state,
        replying: true,
        replyError: null,
    })),
    on(replyInboxEmailSuccess, (state) => ({
        ...state,
        replying: false,
    })),
    on(replyInboxEmailFailure, (state, { error }) => ({
        ...state,
        replying: false,
        replyError: error,
    })),
    on(forwardInboxEmail, (state) => ({
        ...state,
        forwarding: true,
        forwardError: null,
    })),
    on(forwardInboxEmailSuccess, (state) => ({
        ...state,
        forwarding: false,
    })),
    on(forwardInboxEmailFailure, (state, { error }) => ({
        ...state,
        forwarding: false,
        forwardError: error,
    })),
);
