import { AsyncPipe } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Store } from '@ngrx/store';
import {
    BobPlatformLicense,
    BobPlatformMembership,
    BobPlatformRole,
    BobPlatformSettingsSnapshot,
    BobPlatformTenant,
    BobPlatformUser,
} from '../../../shared/services/bob-platform-settings.service';
import {
    inviteBobPlatformUser,
    loadBobPlatformSettings,
    updateBobPlatformLicense,
    updateBobPlatformMembership,
    updateBobPlatformTenant,
} from '../../../store/bob-platform-settings/bob-platform-settings.actions';
import {
    selectBobPlatformSettingsData,
    selectBobPlatformSettingsError,
    selectBobPlatformSettingsLoading,
    selectBobPlatformSettingsNotice,
    selectBobPlatformSettingsSaving,
} from '../../../store/bob-platform-settings/bob-platform-settings.selectors';

@Component({
    selector: 'croo-settings-platform-access',
    standalone: true,
    imports: [AsyncPipe, FormsModule],
    templateUrl: './settings-platform-access.html',
    styleUrls: ['../settings-shared.css', './settings-platform-access.css'],
})
export class SettingsPlatformAccessComponent implements OnInit {
    private store = inject(Store);

    data$ = this.store.select(selectBobPlatformSettingsData);
    loading$ = this.store.select(selectBobPlatformSettingsLoading);
    saving$ = this.store.select(selectBobPlatformSettingsSaving);
    error$ = this.store.select(selectBobPlatformSettingsError);
    notice$ = this.store.select(selectBobPlatformSettingsNotice);

    tenantName = '';
    tenantStatus: BobPlatformTenant['status'] = 'active';
    inviteEmail = '';
    inviteName = '';
    inviteRole = 'support';
    selectedMembershipRoles: Record<string, string> = {};

    ngOnInit(): void {
        this.store.dispatch(loadBobPlatformSettings());
    }

    refresh(): void {
        this.store.dispatch(loadBobPlatformSettings());
    }

    stageTenant(tenant: BobPlatformTenant): void {
        this.tenantName = tenant.name;
        this.tenantStatus = tenant.status;
    }

    saveTenant(tenant: BobPlatformTenant): void {
        if (!this.tenantName.trim()) return;
        this.store.dispatch(updateBobPlatformTenant({
            tenantId: tenant.id,
            payload: {
                name: this.tenantName.trim(),
                status: this.tenantStatus,
            },
        }));
    }

    setLicenseStatus(license: BobPlatformLicense, status: 'enabled' | 'disabled' | 'preview'): void {
        this.store.dispatch(updateBobPlatformLicense({
            code: license.code,
            payload: {
                status,
                remaining: license.remaining,
                limit: license.limit,
            },
        }));
    }

    inviteUser(firstTenantId: string | undefined): void {
        if (!this.inviteEmail.trim()) return;
        this.store.dispatch(inviteBobPlatformUser({
            payload: {
                email: this.inviteEmail.trim(),
                display_name: this.inviteName.trim() || undefined,
                tenant_id: firstTenantId,
                role_codes: [this.inviteRole],
            },
        }));
        this.inviteEmail = '';
        this.inviteName = '';
        this.inviteRole = 'support';
    }

    membershipRole(membership: BobPlatformMembership): string {
        if (!this.selectedMembershipRoles[membership.id]) {
            this.selectedMembershipRoles[membership.id] = membership.role_codes[0] || 'support';
        }
        return this.selectedMembershipRoles[membership.id];
    }

    setMembershipRole(membership: BobPlatformMembership, roleCode: string): void {
        this.selectedMembershipRoles[membership.id] = roleCode;
        this.store.dispatch(updateBobPlatformMembership({
            membershipId: membership.id,
            payload: { role_codes: [roleCode] },
        }));
    }

    userLabel(data: BobPlatformSettingsSnapshot, userId: string): string {
        const user = data.users.find((item) => item.id === userId);
        if (!user) return userId;
        return user.display_name || user.email;
    }

    userEmail(data: BobPlatformSettingsSnapshot, userId: string): string {
        return data.users.find((item) => item.id === userId)?.email || '';
    }

    roleLabel(roles: BobPlatformRole[], roleCode: string): string {
        return roles.find((role) => role.code === roleCode)?.label || roleCode;
    }

    licenseUsage(license: BobPlatformLicense): number {
        if (!license.limit || license.limit <= 0) return 0;
        const used = Math.max(license.limit - (license.remaining || 0), 0);
        return Math.min(Math.round((used / license.limit) * 100), 100);
    }

    statusBadgeClass(status: string | undefined): string {
        switch (status) {
            case 'enabled':
            case 'active':
                return 'status-badge--green';
            case 'preview':
            case 'pending':
                return 'status-badge--blue';
            case 'disabled':
            case 'suspended':
                return 'status-badge--gray';
            default:
                return 'status-badge--purple';
        }
    }

    trackById(_index: number, item: { id: string }): string {
        return item.id;
    }

    trackByCode(_index: number, item: { code: string }): string {
        return item.code;
    }

    trackUser(_index: number, item: BobPlatformUser): string {
        return item.id;
    }
}
