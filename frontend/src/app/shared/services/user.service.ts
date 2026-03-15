import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { User, UserListResponse, CreateUserDto, UpdateUserDto } from '../models/user.model';

const API_URL = `${environment.authApiUrl}`;

@Injectable({ providedIn: 'root' })
export class UserService {
    private http = inject(HttpClient);

    /** GET /auth/me — current user */
    getMe(): Observable<User> {
        return this.http.get<User>(`${API_URL}/auth/me`);
    }

    /** PUT /users/me — update own profile */
    updateMe(data: UpdateUserDto): Observable<User> {
        return this.http.put<User>(`${API_URL}/users/me`, data);
    }

    /** GET /users — list all tenant users */
    getAll(skip = 0, limit = 50): Observable<UserListResponse> {
        return this.http.get<UserListResponse>(`${API_URL}/users?skip=${skip}&limit=${limit}`);
    }

    /** POST /users — create user (admin) */
    create(data: CreateUserDto): Observable<User> {
        return this.http.post<User>(`${API_URL}/users`, data);
    }

    /** DELETE /users/:id — soft delete */
    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/users/${id}`);
    }

    /** PATCH /users/:id — admin update user */
    update(id: string, data: Partial<UpdateUserDto>): Observable<User> {
        return this.http.patch<User>(`${API_URL}/users/${id}`, data);
    }
}
