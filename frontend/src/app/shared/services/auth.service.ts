import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, tap, catchError, throwError, map } from 'rxjs';
import { isPlatformBrowser } from '@angular/common';
import { PLATFORM_ID } from '@angular/core';
import { environment } from '../../../environments/environment';
import { LoginRequest, RegisterRequest, TokenResponse, AuthUser } from '../models/auth.model';

const API_URL = `${environment.authApiUrl}/auth`;
const TOKEN_KEY = 'croo_access_token';
const REFRESH_KEY = 'croo_refresh_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
    private http = inject(HttpClient);
    private router = inject(Router);
    private platformId = inject(PLATFORM_ID);

    private currentUser$ = new BehaviorSubject<AuthUser | null>(null);
    private isAuthenticated$ = new BehaviorSubject<boolean>(this.hasToken());

    user$ = this.currentUser$.asObservable();
    authenticated$ = this.isAuthenticated$.asObservable();
    activeOrgId$ = this.currentUser$.pipe(map(u => u?.active_organization_id ?? null));
    activeOrgName$ = this.currentUser$.pipe(map(u => u?.active_organization_name ?? null));

    constructor() {
        if (this.hasToken()) {
            // Defer execution to avoid NG0200 Circular Dependency with authInterceptor
            // authInterceptor injects AuthService, which fails if AuthService is still instantiating
            setTimeout(() => this.loadCurrentUser(), 0);
        }
    }

    login(credentials: LoginRequest): Observable<TokenResponse> {
        return this.http.post<TokenResponse>(`${API_URL}/login`, credentials).pipe(
            tap((response) => {
                this.storeTokens(response);
                this.isAuthenticated$.next(true);
                this.loadCurrentUser(true);
            }),
            catchError((error) => {
                return throwError(() => error);
            }),
        );
    }

    register(data: RegisterRequest): Observable<AuthUser> {
        return this.http.post<AuthUser>(`${API_URL}/register`, data);
    }

    logout(): void {
        if (isPlatformBrowser(this.platformId)) {
            localStorage.removeItem(TOKEN_KEY);
            localStorage.removeItem(REFRESH_KEY);
        }
        this.currentUser$.next(null);
        this.isAuthenticated$.next(false);
        this.router.navigate(['/login']);
    }

    setActiveOrganization(orgId: string): Observable<AuthUser> {
        return this.http.put<AuthUser>(`${API_URL}/me/active-organization`, {
            organization_id: orgId,
        }).pipe(
            tap((user) => {
                this.currentUser$.next(user);
                this.router.navigate(['/dashboard']);
            }),
        );
    }

    refreshToken(): Observable<TokenResponse> {
        let refreshToken = null;
        if (isPlatformBrowser(this.platformId)) {
            refreshToken = localStorage.getItem(REFRESH_KEY);
        }
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
        if (isPlatformBrowser(this.platformId)) {
            return localStorage.getItem(TOKEN_KEY);
        }
        return null;
    }

    hasToken(): boolean {
        if (isPlatformBrowser(this.platformId)) {
            return !!localStorage.getItem(TOKEN_KEY);
        }
        return false;
    }

    private storeTokens(response: TokenResponse): void {
        if (isPlatformBrowser(this.platformId)) {
            localStorage.setItem(TOKEN_KEY, response.access_token);
            localStorage.setItem(REFRESH_KEY, response.refresh_token);
        }
    }

    private loadCurrentUser(isLogin = false): void {
        this.http.get<AuthUser>(`${API_URL}/me`).subscribe({
            next: (user) => {
                this.currentUser$.next(user);
                if (isLogin && !user.active_organization_id) {
                    this.router.navigate(['/select-organization']);
                }
            },
            error: (err) => {
                console.error('[AuthService] /me request failed during loadCurrentUser:', err);
                if (err && err.status === 401) {
                    console.error('[AuthService] Forcing logout due to 401 from /me');
                    this.logout();
                }
            },
        });
    }
}
