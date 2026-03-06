import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const authService = inject(AuthService);
    const token = authService.getToken();

    // Skip auth header for login/register requests
    if (req.url.includes('/auth/login') || req.url.includes('/auth/register')) {
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
            if (error.status === 401 && !req.url.includes('/auth/refresh')) {
                // Try to refresh the token
                return authService.refreshToken().pipe(
                    switchMap((tokenResponse) => {
                        const retryReq = req.clone({
                            setHeaders: {
                                Authorization: `Bearer ${tokenResponse.access_token}`,
                            },
                        });
                        return next(retryReq);
                    }),
                    catchError(() => {
                        authService.logout();
                        return throwError(() => error);
                    }),
                );
            }
            return throwError(() => error);
        }),
    );
};
