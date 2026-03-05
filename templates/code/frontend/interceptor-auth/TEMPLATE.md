# Template: Intercepteur HTTP d'Authentification (Angular)

> Recette pour injecter le Bearer token sur chaque requête HTTP.
> **Zéro décision** : suivre exactement ce pattern.

## Fichier à créer

`core/interceptors/auth.interceptor.ts`

```typescript
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';

import { Store } from '@ngrx/store';
import { take, switchMap } from 'rxjs/operators';

import { selectAccessToken } from '../../store/auth/auth.selectors';
import { CookieService } from '../services/cookie.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  // Ignorer les fichiers statiques
  if (req.url.startsWith('/data/') || req.url.startsWith('/assets/') || req.url.endsWith('.json')) {
    return next(req);
  }

  // Ne pas écraser un header Authorization existant
  if (req.headers.has('Authorization')) {
    return next(req);
  }

  const store = inject(Store);
  const cookieService = inject(CookieService);

  // Ne pas ajouter le token pour les routes d'auth
  if (req.url.includes('/auth/login') || req.url.includes('/auth/register')) {
    return next(req);
  }

  // Récupérer le token depuis le store ou cookies/storage (fallback)
  return store.select(selectAccessToken).pipe(
    take(1),
    switchMap((token) => {
      let accessToken = token
        || cookieService.get('access_token')
        || localStorage.getItem('access_token')
        || sessionStorage.getItem('access_token');

      // Guard against invalid token values
      if (accessToken && (accessToken === 'undefined' || accessToken === 'null' || accessToken.length < 20)) {
        accessToken = null;
      }

      if (accessToken) {
        const clonedReq = req.clone({
          setHeaders: {
            Authorization: `Bearer ${accessToken}`,
          },
        });
        return next(clonedReq);
      }
      return next(req);
    })
  );
};
```

## Enregistrement dans `app.config.ts`

```typescript
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { authInterceptor } from './core/interceptors/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withInterceptors([authInterceptor])),
  ],
};
```

## Règles NON-NÉGOCIABLES

1. Intercepteur fonctionnel (`HttpInterceptorFn`) — pas de classe
2. Ignorer les fichiers statiques et les routes d'auth
3. Ne pas écraser un header Authorization existant
4. Vérifier la validité du token (pas `undefined`, pas `null`, longueur > 20)
5. Store NgRx en priorité, cookies/storage en fallback
