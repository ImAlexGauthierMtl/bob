import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { AuthSession } from '../models/auth.model';
import { User, UserListResponse, CreateUserDto, UpdateUserDto } from '../models/user.model';

const API_URL = `${environment.authApiUrl}`;
const AUTH_V1_URL = environment.authApiUrl.endsWith('/api/auth/v1')
    ? environment.authApiUrl
    : `${environment.authApiUrl}/api/auth/v1`;

@Injectable({ providedIn: 'root' })
export class UserService {
    private http = inject(HttpClient);

    /** GET /api/auth/v1/session — current Bob Cloud user */
    getMe(): Observable<User> {
        return this.http.get<AuthSession>(`${AUTH_V1_URL}/session`, { withCredentials: true }).pipe(
            map((session) => {
                const sessionUser = session.user || { id: '', email: '' };
                const displayName = (sessionUser.display_name || '').trim();
                const displayParts = displayName ? displayName.split(/\s+/) : [];
                return {
                    id: sessionUser.id,
                    email: sessionUser.email || '',
                    first_name: sessionUser.first_name || displayParts[0] || sessionUser.email || 'User',
                    last_name: sessionUser.last_name || displayParts.slice(1).join(' '),
                    job_title: null,
                    phone: null,
                    bio: null,
                    location: null,
                    timezone: null,
                    role: session.platform_roles?.[0] || 'member',
                    created_at: '',
                    updated_at: '',
                };
            }),
        );
    }

    /** PUT /users/me — update own profile */
    updateMe(data: UpdateUserDto): Observable<User> {
        return this.http.put<User>(`${API_URL}/users/me`, data, { withCredentials: true });
    }

    /** GET /users — list all tenant users */
    getAll(skip = 0, limit = 50): Observable<UserListResponse> {
        return this.http.get<UserListResponse>(`${API_URL}/users?skip=${skip}&limit=${limit}`, { withCredentials: true });
    }

    /** POST /users — create user (admin) */
    create(data: CreateUserDto): Observable<User> {
        return this.http.post<User>(`${API_URL}/users`, data, { withCredentials: true });
    }

    /** DELETE /users/:id — soft delete */
    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/users/${id}`, { withCredentials: true });
    }

    /** PATCH /users/:id — admin update user */
    update(id: string, data: Partial<UpdateUserDto>): Observable<User> {
        return this.http.patch<User>(`${API_URL}/users/${id}`, data, { withCredentials: true });
    }
}
