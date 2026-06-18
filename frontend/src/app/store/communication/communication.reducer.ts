import { createReducer, on } from '@ngrx/store';
import { CommunicationIntegrationOverview } from '../../shared/services/communication-b4f.service';
import { initialRemoteState, RemoteState } from '../remote-state';
import { loadCommunicationOverview, loadCommunicationOverviewFailure, loadCommunicationOverviewSuccess } from './communication.actions';

export type CommunicationState = RemoteState<CommunicationIntegrationOverview>;

export const communicationReducer = createReducer(
    initialRemoteState<CommunicationIntegrationOverview>(),
    on(loadCommunicationOverview, (state) => ({ ...state, loading: true, error: null })),
    on(loadCommunicationOverviewSuccess, (_state, { data }) => ({ data, loading: false, error: null })),
    on(loadCommunicationOverviewFailure, (state, { error }) => ({ ...state, loading: false, error })),
);
