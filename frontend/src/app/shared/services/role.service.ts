import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Role, CreateRoleDto, UpdateRoleDto, RoleListResponse, Permission } from '../models/role.model';

@Injectable({ providedIn: 'root' })
export class RoleService {
    private http = inject(HttpClient);
    private readonly API = `${environment.apiUrl}/roles`;

    getAll(): Observable<RoleListResponse> {
        return this.http.get<RoleListResponse>(this.API);
    }

    getById(id: string): Observable<Role> {
        return this.http.get<Role>(`${this.API}/${id}`);
    }

    create(dto: CreateRoleDto): Observable<Role> {
        return this.http.post<Role>(this.API, dto);
    }

    update(id: string, dto: UpdateRoleDto): Observable<Role> {
        return this.http.patch<Role>(`${this.API}/${id}`, dto);
    }

    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${this.API}/${id}`);
    }

    /** GET /roles/permissions — toutes les permissions système */
    getPermissions(): Observable<Permission[]> {
        return this.http.get<Permission[]>(`${this.API}/permissions`);
    }

    /** PUT /roles/:id/permissions — remplacer les permissions d'un rôle */
    setPermissions(roleId: string, permissionIds: string[]): Observable<Role> {
        return this.http.put<Role>(`${this.API}/${roleId}/permissions`, { permission_ids: permissionIds });
    }
}
