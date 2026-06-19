import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface BobPlatformTenant {
    id: string;
    name: string;
    status: 'active' | 'suspended' | 'disabled';
    hierarchy_path?: string;
    scope?: string;
}

export interface BobPlatformLicense {
    code: string;
    source?: string;
    status: 'enabled' | 'disabled' | 'preview' | string;
    remaining?: number;
    limit?: number;
}

export interface BobPlatformUser {
    id: string;
    email: string;
    display_name?: string;
    status?: string;
}

export interface BobPlatformRole {
    id: string;
    code: string;
    label?: string;
}

export interface BobPlatformMembership {
    id: string;
    tenant_id: string;
    user_id: string;
    role_codes: string[];
    status: 'active' | 'pending' | 'disabled' | string;
}

export interface BobPlatformList<T> {
    items: T[];
    source?: string;
}

export interface BobPlatformLicenseList extends BobPlatformList<BobPlatformLicense> {
    tenant_id?: string;
    module_entitlements?: Record<string, string>;
}

export interface BobPlatformInvitationRequest {
    email: string;
    display_name?: string;
    tenant_id?: string;
    role_codes?: string[];
}

export interface BobPlatformInvitation {
    id: string;
    tenant_id?: string;
    user_id?: string;
    membership_id?: string;
    email: string;
    display_name?: string;
    role_codes?: string[];
    status: string;
    source?: string;
}

export interface BobPlatformSettingsSnapshot {
    tenants: BobPlatformTenant[];
    licenses: BobPlatformLicense[];
    moduleEntitlements: Record<string, string>;
    users: BobPlatformUser[];
    roles: BobPlatformRole[];
    memberships: BobPlatformMembership[];
}

@Injectable({ providedIn: 'root' })
export class BobPlatformSettingsService {
    private http = inject(HttpClient);
    private baseUrl = `${environment.bobSettingsApiUrl}/security`;

    listTenants(): Observable<BobPlatformList<BobPlatformTenant>> {
        return this.http.get<BobPlatformList<BobPlatformTenant>>(`${this.baseUrl}/tenants`);
    }

    updateTenant(tenantId: string, payload: Partial<BobPlatformTenant>): Observable<BobPlatformTenant> {
        return this.http.patch<BobPlatformTenant>(
            `${this.baseUrl}/tenants/${encodeURIComponent(tenantId)}`,
            payload,
            { headers: this.idempotencyHeaders('tenant') },
        );
    }

    listLicenses(): Observable<BobPlatformLicenseList> {
        return this.http.get<BobPlatformLicenseList>(`${this.baseUrl}/licenses`);
    }

    updateLicense(code: string, payload: Partial<BobPlatformLicense>): Observable<BobPlatformLicense> {
        return this.http.patch<BobPlatformLicense>(
            `${this.baseUrl}/licenses/${encodeURIComponent(code)}`,
            payload,
            { headers: this.idempotencyHeaders('license') },
        );
    }

    listUsers(): Observable<BobPlatformList<BobPlatformUser>> {
        return this.http.get<BobPlatformList<BobPlatformUser>>(`${this.baseUrl}/users`);
    }

    createInvitation(payload: BobPlatformInvitationRequest): Observable<BobPlatformInvitation> {
        return this.http.post<BobPlatformInvitation>(
            `${this.baseUrl}/invitations`,
            payload,
            { headers: this.idempotencyHeaders('invite') },
        );
    }

    listRoles(): Observable<BobPlatformList<BobPlatformRole>> {
        return this.http.get<BobPlatformList<BobPlatformRole>>(`${this.baseUrl}/roles`);
    }

    listMemberships(): Observable<BobPlatformList<BobPlatformMembership>> {
        return this.http.get<BobPlatformList<BobPlatformMembership>>(`${this.baseUrl}/memberships`);
    }

    updateMembership(
        membershipId: string,
        payload: Partial<BobPlatformMembership>,
    ): Observable<BobPlatformMembership> {
        return this.http.patch<BobPlatformMembership>(
            `${this.baseUrl}/memberships/${encodeURIComponent(membershipId)}`,
            payload,
            { headers: this.idempotencyHeaders('membership') },
        );
    }

    private idempotencyHeaders(prefix: string): HttpHeaders {
        return new HttpHeaders({ 'Idempotency-Key': `${prefix}-${this.randomId()}` });
    }

    private randomId(): string {
        if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
            return crypto.randomUUID();
        }
        return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    }
}
