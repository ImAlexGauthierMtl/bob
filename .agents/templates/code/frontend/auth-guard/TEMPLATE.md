# Template: Auth Guard (Angular)

> Recette pour créer un guard d'authentification fonctionnel.
> **Zéro décision** : suivre exactement ce pattern.

## Fichier à créer

`core/guards/auth.guard.ts`

```typescript
import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';

import { CookieService } from '../services/cookie.service';

export const authGuard: CanActivateFn = (_route, _state) => {
  const router = inject(Router);
  const cookieService = inject(CookieService);

  const accessToken = cookieService.get('access_token')
    || localStorage.getItem('access_token')
    || sessionStorage.getItem('access_token');
  const refreshToken = cookieService.get('refresh_token')
    || localStorage.getItem('refresh_token')
    || sessionStorage.getItem('refresh_token');

  if (accessToken && refreshToken) {
    return true;
  }

  router.navigate(['/auth/login']);
  return false;
};
```

## Test — `core/guards/auth.guard.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { authGuard } from './auth.guard';
import { CookieService } from '../services/cookie.service';

describe('authGuard', () => {
  let router: Router;
  let cookieService: jasmine.SpyObj<CookieService>;

  beforeEach(() => {
    cookieService = jasmine.createSpyObj('CookieService', ['get']);
    TestBed.configureTestingModule({
      providers: [
        { provide: CookieService, useValue: cookieService },
      ],
    });
    router = TestBed.inject(Router);
    spyOn(router, 'navigate');
  });

  it('should allow access when tokens exist', () => {
    cookieService.get.and.returnValue('valid-token');
    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as any, {} as any)
    );
    expect(result).toBeTrue();
  });

  it('should redirect to login when no tokens', () => {
    cookieService.get.and.returnValue(null);
    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as any, {} as any)
    );
    expect(result).toBeFalse();
    expect(router.navigate).toHaveBeenCalledWith(['/auth/login']);
  });
});
```

## Règles NON-NÉGOCIABLES

1. Guard fonctionnel (`CanActivateFn`) — pas de classe
2. Vérifier cookies d'abord, puis localStorage/sessionStorage en fallback
3. Redirect vers `/auth/login` si pas de tokens
4. `inject()` pour les dépendances (pas de constructeur)
