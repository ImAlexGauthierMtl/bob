import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = () => {
    const authService = inject(AuthService);
    const router = inject(Router);

    return authService.ensureSession().pipe(
        map((session) => session.authenticated ? true : router.createUrlTree(['/login'])),
        catchError(() => of(router.createUrlTree(['/login']))),
    );
};
