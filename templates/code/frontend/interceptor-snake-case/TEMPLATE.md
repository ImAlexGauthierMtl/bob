# Template: Intercepteur snake_case → camelCase (Angular)

> Recette pour convertir automatiquement les réponses API de snake_case vers camelCase.
> **Zéro décision** : suivre exactement ce pattern.

## Fichiers à créer (2 fichiers)

### 1. `core/utils/snake-to-camel.ts` — Utilitaire de conversion

```typescript
/**
 * Convert snake_case string to camelCase.
 */
function toCamelCase(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * Recursively convert all keys of an object from snake_case to camelCase.
 */
export function snakeToCamel(obj: unknown): unknown {
  if (Array.isArray(obj)) {
    return obj.map(snakeToCamel);
  }

  if (obj !== null && typeof obj === 'object' && !(obj instanceof Date)) {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      result[toCamelCase(key)] = snakeToCamel(value);
    }
    return result;
  }

  return obj;
}
```

### 2. `core/interceptors/snake-case-response.interceptor.ts`

```typescript
import {
  HttpInterceptorFn,
  HttpResponse,
  HttpErrorResponse,
} from '@angular/common/http';

import { map, catchError, throwError } from 'rxjs';

import { snakeToCamel } from '../utils/snake-to-camel';

/**
 * Interceptor that converts JSON response bodies from snake_case keys to camelCase.
 * Backend APIs return snake_case; frontend models expect camelCase.
 */
export const snakeCaseResponseInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    map((event) => {
      if (event instanceof HttpResponse && event.body != null) {
        const contentType = event.headers.get('Content-Type')?.toLowerCase() ?? '';
        if (contentType.includes('application/json')) {
          const converted = snakeToCamel(event.body);
          return event.clone({ body: converted });
        }
      }
      return event;
    }),
    catchError((err) => {
      if (err instanceof HttpErrorResponse && err.error != null) {
        const contentType = err.headers?.get('Content-Type')?.toLowerCase() ?? '';
        if (contentType.includes('application/json') && typeof err.error === 'object') {
          const converted = snakeToCamel(err.error);
          return throwError(
            () =>
              new HttpErrorResponse({
                error: converted,
                headers: err.headers,
                status: err.status,
                statusText: err.statusText,
                url: err.url ?? undefined,
              })
          );
        }
      }
      return throwError(() => err);
    })
  );
};
```

## Enregistrement dans `app.config.ts`

```typescript
provideHttpClient(withInterceptors([
  snakeCaseResponseInterceptor,
  authInterceptor,
])),
```

## Règles NON-NÉGOCIABLES

1. Convertir uniquement les réponses JSON (`Content-Type: application/json`)
2. Conversion récursive (objets imbriqués, arrays)
3. Gérer les erreurs aussi (HttpErrorResponse) pour uniformité
4. Placer AVANT `authInterceptor` dans la chaîne
5. Ne pas convertir les objets `Date`
