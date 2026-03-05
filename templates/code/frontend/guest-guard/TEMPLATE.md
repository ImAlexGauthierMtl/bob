# Template: Guest Guard (Angular)

> Recette pour créer un guard empêchant l'accès aux pages auth si déjà connecté.
> **Zéro décision** : suivre exactement ce pattern.

## Fichier à créer

`core/guards/guest.guard.ts`

```typescript
import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';

import { CookieService } from '../services/cookie.service';

export const guestGuard: CanActivateFn = (_route, _state) => {
  const router = inject(Router);
  const cookieService = inject(CookieService);

  const accessToken = cookieService.get('access_token')
    || localStorage.getItem('access_token')
    || sessionStorage.getItem('access_token');
  const refreshToken = cookieService.get('refresh_token')
    || localStorage.getItem('refresh_token')
    || sessionStorage.getItem('refresh_token');

  if (accessToken && refreshToken) {
    // User is authenticated — redirect to dashboard
    router.navigate(['/admin/dashboard']);
    return false;
  }

  // No tokens — allow access to login/register pages
  return true;
};
```

## Règles NON-NÉGOCIABLES

1. Guard fonctionnel (`CanActivateFn`)
2. Redirect vers `/admin/dashboard` si déjà authentifié
3. Utiliser le même check de token que `authGuard`
4. Appliquer sur les routes `/auth/login` et `/auth/register`
