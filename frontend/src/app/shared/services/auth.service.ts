import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, tap, catchError, throwError, map, of } from 'rxjs';
import { environment } from '../../../environments/environment';
import { LoginRequest, RegisterRequest, AuthSession, AuthUser } from '../models/auth.model';

const AUTH_V1_URL = environment.authApiUrl.endsWith('/api/auth/v1')
    ? environment.authApiUrl
    : `${environment.authApiUrl}/api/auth/v1`;

const LEGACY_AUTH_URL = environment.authApiUrl.endsWith('/api/auth/v1')
    ? environment.authApiUrl.replace(/\/api\/auth\/v1$/, '/auth')
    : `${environment.authApiUrl}/auth`;

@Injectable({ providedIn: 'root' })
export class AuthService {
    private http = inject(HttpClient);
    private router = inject(Router);

    private currentUser$ = new BehaviorSubject<AuthUser | null>(null);
    private isAuthenticated$ = new BehaviorSubject<boolean>(false);
    private currentSession$ = new BehaviorSubject<AuthSession | null>(null);

    user$ = this.currentUser$.asObservable();
    authenticated$ = this.isAuthenticated$.asObservable();
    session$ = this.currentSession$.asObservable();
    activeOrgId$ = this.currentUser$.pipe(map(u => u?.active_organization_id ?? null));
    activeOrgName$ = this.currentUser$.pipe(map(u => u?.active_organization_name ?? null));

    constructor() {
        // Defer execution to avoid NG0200 Circular Dependency with authInterceptor
        // authInterceptor injects AuthService, which fails if AuthService is still instantiating.
        setTimeout(() => this.ensureSession().subscribe({ error: () => this.clearSession() }), 0);
    }

    login(_credentials: LoginRequest): Observable<AuthSession> {
        return this.ensureSession().pipe(
            tap((session) => {
                if (!session.authenticated) {
                    throw new Error('Bob Cloud session is not authenticated');
                }
            }),
            catchError((error) => {
                return throwError(() => error);
            }),
        );
    }

    register(data: RegisterRequest): Observable<AuthUser> {
        return this.http.post<AuthUser>(`${LEGACY_AUTH_URL}/register`, data, { withCredentials: true });
    }

    logout(): void {
        this.http.post<AuthSession>(`${AUTH_V1_URL}/logout`, {}, { withCredentials: true }).subscribe({
            next: () => this.clearSessionAndRedirect(),
            error: () => this.clearSessionAndRedirect(),
        });
    }

    setActiveOrganization(orgId: string): Observable<AuthUser> {
        return this.http.put<AuthUser>(`${LEGACY_AUTH_URL}/me/active-organization`, {
            organization_id: orgId,
        }, { withCredentials: true }).pipe(
            tap((user) => {
                this.currentUser$.next(user);
                this.router.navigate(['/dashboard']);
            }),
        );
    }

    ensureSession(): Observable<AuthSession> {
        return this.http
            .get<AuthSession>(`${AUTH_V1_URL}/session`, { withCredentials: true })
            .pipe(
                tap((session) => this.applySession(session)),
                catchError((error) => {
                    this.clearSession();
                    return throwError(() => error);
                }),
            );
    }

    refreshSession(): Observable<AuthSession> {
        return this.http
            .post<AuthSession>(`${AUTH_V1_URL}/refresh`, {}, { withCredentials: true })
            .pipe(
                tap((session) => this.applySession(session)),
                catchError((error) => {
                    this.clearSession();
                    return throwError(() => error);
                }),
            );
    }

    hasActiveSession(): boolean {
        return this.isAuthenticated$.value;
    }

    clearSession(): void {
        this.currentSession$.next(null);
        this.currentUser$.next(null);
        this.isAuthenticated$.next(false);
    }

    clearSessionAndRedirect(): void {
        this.clearSession();
        this.router.navigate(['/login']);
    }

    currentUserSnapshot(): AuthUser | null {
        return this.currentUser$.value;
    }

    getCurrentUser(): Observable<AuthUser | null> {
        const cachedUser = this.currentUser$.value;
        if (cachedUser) {
            return of(cachedUser);
        }
        return this.ensureSession().pipe(map(() => this.currentUser$.value));
    }

    private applySession(session: AuthSession): void {
        this.currentSession$.next(session);
        this.isAuthenticated$.next(!!session.authenticated);
        this.currentUser$.next(session.authenticated && session.user ? this.mapSessionUser(session) : null);
    }

    private mapSessionUser(session: AuthSession): AuthUser {
        const sessionUser = session.user || { id: '', email: '' };
        const displayName = (sessionUser.display_name || '').trim();
        const displayParts = displayName ? displayName.split(/\s+/) : [];
        const firstName = sessionUser.first_name || displayParts[0] || sessionUser.email || 'User';
        const lastName = sessionUser.last_name || displayParts.slice(1).join(' ');
        const role = session.platform_roles?.[0] || 'member';

        return {
            id: sessionUser.id,
            email: sessionUser.email || '',
            first_name: firstName,
            last_name: lastName,
            active_organization_id: session.tenant?.id || null,
            active_organization_name: session.tenant?.name || null,
            role,
            is_super_admin: session.platform_roles?.includes('admin') ?? false,
            created_at: '',
            updated_at: '',
        };
    }
}
