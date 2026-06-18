import { createReducer, on } from '@ngrx/store';
import { PlatformOverview } from '../../shared/services/platform-b4f.service';
import { initialRemoteState, RemoteState } from '../remote-state';
import { loadPlatformOverview, loadPlatformOverviewFailure, loadPlatformOverviewSuccess } from './platform.actions';

export type PlatformState = RemoteState<PlatformOverview>;

export const platformReducer = createReducer(
    initialRemoteState<PlatformOverview>(),
    on(loadPlatformOverview, (state) => ({ ...state, loading: true, error: null })),
    on(loadPlatformOverviewSuccess, (_state, { data }) => ({ data, loading: false, error: null })),
    on(loadPlatformOverviewFailure, (state, { error }) => ({ ...state, loading: false, error })),
);
