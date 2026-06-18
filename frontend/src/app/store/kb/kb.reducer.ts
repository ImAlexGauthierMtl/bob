import { createReducer, on } from '@ngrx/store';
import { KbHome } from '../../shared/services/kb-b4f.service';
import { initialRemoteState, RemoteState } from '../remote-state';
import { loadKbHome, loadKbHomeFailure, loadKbHomeSuccess } from './kb.actions';

export type KbState = RemoteState<KbHome>;

export const kbReducer = createReducer(
    initialRemoteState<KbHome>(),
    on(loadKbHome, (state) => ({ ...state, loading: true, error: null })),
    on(loadKbHomeSuccess, (_state, { data }) => ({ data, loading: false, error: null })),
    on(loadKbHomeFailure, (state, { error }) => ({ ...state, loading: false, error })),
);
