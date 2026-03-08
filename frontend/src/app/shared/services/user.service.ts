import { environment } from '../../../environments/environment';
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface User {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    job_title: string | null;
    phone: string | null;
    bio: string | null;
    location: string | null;
    timezone: string | null;
    role: string;
    created_at: string;
    updated_at: string;
}

export interface UserUpdateRequest {
    first_name?: string;
    last_name?: string;
    job_title?: string;
    phone?: string;
    bio?: string;
    location?: string;
    timezone?: string;
    role?: string;
}

export interface UserCreateRequest {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    role?: string;
    job_title?: string;
    phone?: string;
}

export interface UserListResponse {
    items: User[];
    total: number;
    skip: number;
    limit: number;
}

const API_URL = `${environment.apiUrl}`;

@Injectable({ providedIn: 'root' })
export class UserService {
    constructor(private http: HttpClient) { }

    /** GET /auth/me — current user */
    getMe(): Observable<User> {
        return this.http.get<User>(`${API_URL}/auth/me`);
    }

    /** PUT /users/me — update own profile */
    updateMe(data: UserUpdateRequest): Observable<User> {
        return this.http.put<User>(`${API_URL}/users/me`, data);
    }

    /** GET /users — list all tenant users */
    listUsers(skip = 0, limit = 50): Observable<UserListResponse> {
        return this.http.get<UserListResponse>(`${API_URL}/users?skip=${skip}&limit=${limit}`);
    }

    /** POST /users — create user (admin) */
    createUser(data: UserCreateRequest): Observable<User> {
        return this.http.post<User>(`${API_URL}/users`, data);
    }

    /** DELETE /users/:id — soft delete */
    deleteUser(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/users/${id}`);
    }

    /** PATCH /users/:id — admin update user */
    updateUser(id: string, data: Partial<UserUpdateRequest>): Observable<User> {
        return this.http.patch<User>(`${API_URL}/users/${id}`, data);
    }
}
