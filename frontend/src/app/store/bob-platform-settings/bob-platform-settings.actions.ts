import { createAction, props } from '@ngrx/store';
import {
    BobPlatformInvitationRequest,
    BobPlatformLicense,
    BobPlatformMembership,
    BobPlatformSettingsSnapshot,
    BobPlatformTenant,
} from '../../shared/services/bob-platform-settings.service';

export const loadBobPlatformSettings = createAction('[Bob Platform Settings] Load');
export const loadBobPlatformSettingsSuccess = createAction(
    '[Bob Platform Settings] Load success',
    props<{ data: BobPlatformSettingsSnapshot }>(),
);
export const loadBobPlatformSettingsFailure = createAction(
    '[Bob Platform Settings] Load failure',
    props<{ error: string }>(),
);

export const updateBobPlatformTenant = createAction(
    '[Bob Platform Settings] Update tenant',
    props<{ tenantId: string; payload: Partial<BobPlatformTenant> }>(),
);
export const updateBobPlatformTenantSuccess = createAction(
    '[Bob Platform Settings] Update tenant success',
    props<{ tenant: BobPlatformTenant }>(),
);

export const updateBobPlatformLicense = createAction(
    '[Bob Platform Settings] Update license',
    props<{ code: string; payload: Partial<BobPlatformLicense> }>(),
);
export const updateBobPlatformLicenseSuccess = createAction(
    '[Bob Platform Settings] Update license success',
    props<{ license: BobPlatformLicense }>(),
);

export const inviteBobPlatformUser = createAction(
    '[Bob Platform Settings] Invite user',
    props<{ payload: BobPlatformInvitationRequest }>(),
);
export const inviteBobPlatformUserSuccess = createAction(
    '[Bob Platform Settings] Invite user success',
);

export const updateBobPlatformMembership = createAction(
    '[Bob Platform Settings] Update membership',
    props<{ membershipId: string; payload: Partial<BobPlatformMembership> }>(),
);
export const updateBobPlatformMembershipSuccess = createAction(
    '[Bob Platform Settings] Update membership success',
    props<{ membership: BobPlatformMembership }>(),
);

export const bobPlatformSettingsMutationFailure = createAction(
    '[Bob Platform Settings] Mutation failure',
    props<{ error: string }>(),
);
