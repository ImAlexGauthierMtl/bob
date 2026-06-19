import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { Router } from '@angular/router';

const isAuthSessionRequest = (url: string): boolean => (
    url.includes('/api/auth/v1/session') ||
    url.includes('/api/auth/v1/refresh') ||
    url.includes('/api/auth/v1/logout') ||
    url.includes('/auth/login') ||
    url.includes('/auth/register') ||
    url.includes('/auth/refresh')
);

export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const authService = inject(AuthService);
    const router = inject(Router);
    const accessToken = authService.getAccessToken();
    let credentialRequest = req.withCredentials ? req : req.clone({ withCredentials: true });
    if (accessToken && !credentialRequest.headers.has('Authorization')) {
        credentialRequest = credentialRequest.clone({
            setHeaders: { Authorization: `Bearer ${accessToken}` },
        });
    }

    return next(credentialRequest).pipe(
        catchError((error: HttpErrorResponse) => {
            if (error.status === 0) {
                // Backend unreachable (network error / connection refused) — skip refresh
                console.warn('[AuthInterceptor] Backend unreachable, skipping refresh for:', credentialRequest.url);
                return throwError(() => error);
            }
            if (error.status === 401 && !isAuthSessionRequest(credentialRequest.url)) {
                return authService.refreshSession().pipe(
                    switchMap(() => next(credentialRequest.clone({ withCredentials: true }))),
                    catchError((refreshError) => {
                        if (refreshError?.status !== 0) {
                            authService.clearSessionAndRedirect();
                        }
                        return throwError(() => refreshError);
                    }),
                );
            }
            if (error.status === 403) {
                // Insufficient permissions — navigate to dashboard
                console.warn('[RBAC] Access denied:', error.error?.detail || 'Insufficient permissions');
                router.navigate(['/dashboard']);
                return throwError(() => error);
            }
            return throwError(() => error);
        }),
    );
};
