import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { BehaviorSubject, catchError, filter, switchMap, take, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { Router } from '@angular/router';

// Module-level state for token refresh queuing
let isRefreshing = false;
const refreshTokenSubject = new BehaviorSubject<string | null>(null);

export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const authService = inject(AuthService);
    const token = authService.getToken();

    // Skip auth header for login/register/refresh requests
    if (
        req.url.includes('/auth/login') ||
        req.url.includes('/auth/register') ||
        req.url.includes('/auth/refresh')
    ) {
        return next(req);
    }

    // Add token if available
    if (token) {
        req = req.clone({
            setHeaders: {
                Authorization: `Bearer ${token}`,
            },
        });
    }

    return next(req).pipe(
        catchError((error: HttpErrorResponse) => {
            if (error.status === 401) {
                if (!isRefreshing) {
                    // First 401 — initiate refresh
                    isRefreshing = true;
                    refreshTokenSubject.next(null);

                    return authService.refreshToken().pipe(
                        switchMap((tokenResponse) => {
                            isRefreshing = false;
                            refreshTokenSubject.next(tokenResponse.access_token);
                            const retryReq = req.clone({
                                setHeaders: {
                                    Authorization: `Bearer ${tokenResponse.access_token}`,
                                },
                            });
                            return next(retryReq);
                        }),
                        catchError((refreshError) => {
                            isRefreshing = false;
                            refreshTokenSubject.next(null);
                            authService.logout();
                            return throwError(() => refreshError);
                        }),
                    );
                } else {
                    // Refresh already in progress — wait for it to complete
                    return refreshTokenSubject.pipe(
                        filter((newToken): newToken is string => newToken !== null),
                        take(1),
                        switchMap((newToken) => {
                            const retryReq = req.clone({
                                setHeaders: {
                                    Authorization: `Bearer ${newToken}`,
                                },
                            });
                            return next(retryReq);
                        }),
                    );
                }
            }
            if (error.status === 403) {
                // Insufficient permissions — navigate to dashboard
                const router = inject(Router);
                console.warn('[RBAC] Access denied:', error.error?.detail || 'Insufficient permissions');
                router.navigate(['/dashboard']);
                return throwError(() => error);
            }
            return throwError(() => error);
        }),
    );
};
