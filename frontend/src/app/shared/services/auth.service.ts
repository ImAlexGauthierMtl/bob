import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, tap, catchError, throwError } from 'rxjs';

export interface LoginRequest {
    email: string;
    password: string;
}

export interface RegisterRequest {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
}

export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface User {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    created_at: string;
    updated_at: string;
}

const API_URL = 'http://localhost:8555/api/v1/auth';
const TOKEN_KEY = 'croo_access_token';
const REFRESH_KEY = 'croo_refresh_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
    private currentUser$ = new BehaviorSubject<User | null>(null);
    private isAuthenticated$ = new BehaviorSubject<boolean>(this.hasToken());

    user$ = this.currentUser$.asObservable();
    authenticated$ = this.isAuthenticated$.asObservable();

    constructor(
        private http: HttpClient,
        private router: Router,
    ) {
        if (this.hasToken()) {
            this.loadCurrentUser();
        }
    }

    login(credentials: LoginRequest): Observable<TokenResponse> {
        return this.http.post<TokenResponse>(`${API_URL}/login`, credentials).pipe(
            tap((response) => {
                this.storeTokens(response);
                this.isAuthenticated$.next(true);
                this.loadCurrentUser();
            }),
            catchError((error) => {
                return throwError(() => error);
            }),
        );
    }

    register(data: RegisterRequest): Observable<User> {
        return this.http.post<User>(`${API_URL}/register`, data);
    }

    logout(): void {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        this.currentUser$.next(null);
        this.isAuthenticated$.next(false);
        this.router.navigate(['/login']);
    }

    refreshToken(): Observable<TokenResponse> {
        const refreshToken = localStorage.getItem(REFRESH_KEY);
        return this.http
            .post<TokenResponse>(`${API_URL}/refresh`, {
                refresh_token: refreshToken,
            })
            .pipe(
                tap((response) => {
                    this.storeTokens(response);
                }),
                catchError((error) => {
                    this.logout();
                    return throwError(() => error);
                }),
            );
    }

    getToken(): string | null {
        return localStorage.getItem(TOKEN_KEY);
    }

    hasToken(): boolean {
        return !!localStorage.getItem(TOKEN_KEY);
    }

    private storeTokens(response: TokenResponse): void {
        localStorage.setItem(TOKEN_KEY, response.access_token);
        localStorage.setItem(REFRESH_KEY, response.refresh_token);
    }

    private loadCurrentUser(): void {
        this.http.get<User>(`${API_URL}/me`).subscribe({
            next: (user) => this.currentUser$.next(user),
            error: () => this.logout(),
        });
    }
}
