import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

/* ── Interfaces ───────────────────────────────────────────── */

export interface Permission {
    id: string;
    resource: string;
    action: string;
    description: string | null;
}

export interface Role {
    id: string;
    name: string;
    description: string | null;
    is_system: boolean;
    permissions: Permission[];
}

export interface RoleListResponse {
    items: Role[];
    total: number;
}

export interface RoleCreate {
    name: string;
    description?: string;
}

export interface RoleUpdate {
    name?: string;
    description?: string;
}

const API_URL = `${environment.apiUrl}/roles`;

/* ── Service ──────────────────────────────────────────────── */

@Injectable({ providedIn: 'root' })
export class RoleService {
    constructor(private http: HttpClient) { }

    /** GET /roles — list all roles for tenant */
    listRoles(): Observable<RoleListResponse> {
        return this.http.get<RoleListResponse>(API_URL);
    }

    /** GET /roles/permissions — list all system permissions */
    listPermissions(): Observable<Permission[]> {
        return this.http.get<Permission[]>(`${API_URL}/permissions`);
    }

    /** POST /roles — create custom role */
    createRole(data: RoleCreate): Observable<Role> {
        return this.http.post<Role>(API_URL, data);
    }

    /** PATCH /roles/:id — update role */
    updateRole(id: string, data: RoleUpdate): Observable<Role> {
        return this.http.patch<Role>(`${API_URL}/${id}`, data);
    }

    /** DELETE /roles/:id — delete custom role */
    deleteRole(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/${id}`);
    }

    /** PUT /roles/:id/permissions — replace all permissions */
    setRolePermissions(roleId: string, permissionIds: string[]): Observable<Role> {
        return this.http.put<Role>(`${API_URL}/${roleId}/permissions`, { permission_ids: permissionIds });
    }

    /** GET /roles/:id — get single role */
    getRole(id: string): Observable<Role> {
        return this.http.get<Role>(`${API_URL}/${id}`);
    }
}
