import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, forkJoin, map, mergeMap, of, switchMap } from 'rxjs';
import { BobPlatformSettingsService } from '../../shared/services/bob-platform-settings.service';
import { errorMessage } from '../remote-state';
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

@Injectable()
export class BobPlatformSettingsEffects {
    private actions$ = inject(Actions);
    private service = inject(BobPlatformSettingsService);

    load$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadBobPlatformSettings),
            switchMap(() =>
                forkJoin({
                    tenants: this.service.listTenants(),
                    licenses: this.service.listLicenses(),
                    users: this.service.listUsers(),
                    roles: this.service.listRoles(),
                    memberships: this.service.listMemberships(),
                }).pipe(
                    map(({ tenants, licenses, users, roles, memberships }) =>
                        loadBobPlatformSettingsSuccess({
                            data: {
                                tenants: tenants.items,
                                licenses: licenses.items,
                                moduleEntitlements: licenses.module_entitlements || {},
                                users: users.items,
                                roles: roles.items,
                                memberships: memberships.items,
                            },
                        }),
                    ),
                    catchError((error) => of(loadBobPlatformSettingsFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    updateTenant$ = createEffect(() =>
        this.actions$.pipe(
            ofType(updateBobPlatformTenant),
            mergeMap(({ tenantId, payload }) =>
                this.service.updateTenant(tenantId, payload).pipe(
                    map((tenant) => updateBobPlatformTenantSuccess({ tenant })),
                    catchError((error) => of(bobPlatformSettingsMutationFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    updateLicense$ = createEffect(() =>
        this.actions$.pipe(
            ofType(updateBobPlatformLicense),
            mergeMap(({ code, payload }) =>
                this.service.updateLicense(code, payload).pipe(
                    map((license) => updateBobPlatformLicenseSuccess({ license })),
                    catchError((error) => of(bobPlatformSettingsMutationFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    inviteUser$ = createEffect(() =>
        this.actions$.pipe(
            ofType(inviteBobPlatformUser),
            mergeMap(({ payload }) =>
                this.service.createInvitation(payload).pipe(
                    mergeMap(() => [
                        inviteBobPlatformUserSuccess(),
                        loadBobPlatformSettings(),
                    ]),
                    catchError((error) => of(bobPlatformSettingsMutationFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    updateMembership$ = createEffect(() =>
        this.actions$.pipe(
            ofType(updateBobPlatformMembership),
            mergeMap(({ membershipId, payload }) =>
                this.service.updateMembership(membershipId, payload).pipe(
                    map((membership) => updateBobPlatformMembershipSuccess({ membership })),
                    catchError((error) => of(bobPlatformSettingsMutationFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );
}
