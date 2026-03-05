# Template: Cookie Service (Angular)

> Abstraction pour lire/écrire/supprimer des cookies.

## Fichier

`core/services/cookie.service.ts`

```typescript
import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class CookieService {
  get(name: string): string | null {
    if (typeof document === 'undefined') return null;
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
  }

  set(name: string, value: string, expirationMinutes = 30, path = '/'): void {
    const date = new Date();
    date.setTime(date.getTime() + expirationMinutes * 60 * 1000);
    document.cookie = `${name}=${encodeURIComponent(value)};expires=${date.toUTCString()};path=${path};SameSite=Strict`;
  }

  remove(name: string, path = '/'): void {
    document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=${path}`;
  }

  exists(name: string): boolean {
    return this.get(name) !== null;
  }
}
```

## Règles : SSR-safe (`typeof document`), SameSite=Strict, path `/`.
