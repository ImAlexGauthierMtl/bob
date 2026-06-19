import { createReducer, on } from '@ngrx/store';
import {
    BobPlatformSettingsSnapshot,
} from '../../shared/services/bob-platform-settings.service';
import {
    bobPlatformSettingsMutationFailure,
    inviteBobPlatformUser,
    inviteBobPlatformUserSuccess,
    loadBobPlatformSettings,
    loadBobPlatformSettingsFailure,
    loadBobPlatformSettingsSuccess,
    updateBobPlatformLicense,
    updateBobPlatformLicenseSuccess,
    updateBobPlatformMembership,
    updateBobPlatformMembershipSuccess,
    updateBobPlatformTenant,
    updateBobPlatformTenantSuccess,
} from './bob-platform-settings.actions';

export interface BobPlatformSettingsState {
    data: BobPlatformSettingsSnapshot | null;
    loading: boolean;
    saving: boolean;
    error: string | null;
    notice: string | null;
}

export const initialBobPlatformSettingsState: BobPlatformSettingsState = {
    data: null,
    loading: false,
    saving: false,
    error: null,
    notice: null,
};

export const bobPlatformSettingsReducer = createReducer(
    initialBobPlatformSettingsState,
    on(loadBobPlatformSettings, (state) => ({ ...state, loading: true, error: null })),
    on(loadBobPlatformSettingsSuccess, (_state, { data }) => ({
        data,
        loading: false,
        saving: false,
        error: null,
        notice: null,
    })),
    on(loadBobPlatformSettingsFailure, (state, { error }) => ({
        ...state,
        loading: false,
        error,
    })),
    on(updateBobPlatformTenant, updateBobPlatformLicense, inviteBobPlatformUser, updateBobPlatformMembership, (state) => ({
        ...state,
        saving: true,
        error: null,
        notice: null,
    })),
    on(updateBobPlatformTenantSuccess, (state, { tenant }) => ({
        ...state,
        saving: false,
        data: state.data
            ? { ...state.data, tenants: replaceById(state.data.tenants, tenant) }
            : state.data,
        notice: 'Tenant updated',
    })),
    on(updateBobPlatformLicenseSuccess, (state, { license }) => ({
        ...state,
        saving: false,
        data: state.data
            ? { ...state.data, licenses: replaceByCode(state.data.licenses, license) }
            : state.data,
        notice: 'License updated',
    })),
    on(updateBobPlatformMembershipSuccess, (state, { membership }) => ({
        ...state,
        saving: false,
        data: state.data
            ? { ...state.data, memberships: replaceById(state.data.memberships, membership) }
            : state.data,
        notice: 'Membership updated',
    })),
    on(inviteBobPlatformUserSuccess, (state) => ({
        ...state,
        saving: false,
        notice: 'Invitation created',
    })),
    on(bobPlatformSettingsMutationFailure, (state, { error }) => ({
        ...state,
        saving: false,
        error,
    })),
);

function replaceById<T extends { id: string }>(items: T[], item: T): T[] {
    return items.map((current) => current.id === item.id ? item : current);
}

function replaceByCode<T extends { code: string }>(items: T[], item: T): T[] {
    return items.map((current) => current.code === item.code ? item : current);
}
