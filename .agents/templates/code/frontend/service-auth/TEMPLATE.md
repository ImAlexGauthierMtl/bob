# Template: Service d'Authentification (Angular)

> Recette pour créer le service d'authentification complet.
> **Zéro décision** : suivre exactement ce pattern.

## Fichiers à créer (3 fichiers)

### 1. `core/models/auth.models.ts`

```typescript
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  // camelCase aliases (post-interceptor)
  accessToken?: string;
  refreshToken?: string;
  tokenType?: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface UserResponse {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  created_at: string;
  updated_at: string;
  // camelCase aliases
  firstName?: string;
  lastName?: string;
  createdAt?: string;
  updatedAt?: string;
}
```

### 2. `core/services/cookie.service.ts`

```typescript
import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class CookieService {
  get(name: string): string | null {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
  }

  set(name: string, value: string, expirationMinutes: number = 30): void {
    const date = new Date();
    date.setTime(date.getTime() + expirationMinutes * 60 * 1000);
    document.cookie = `${name}=${encodeURIComponent(value)};expires=${date.toUTCString()};path=/;SameSite=Strict`;
  }

  remove(name: string): void {
    document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/`;
  }
}
```

### 3. `core/services/auth.service.ts`

```typescript
import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { Observable, of } from 'rxjs';
import { map, switchMap, catchError, tap, timeout, retry } from 'rxjs/operators';

import { UserResponse, TokenResponse, LoginRequest, RegisterRequest, RefreshTokenRequest } from '../models/auth.models';
import { CookieService } from './cookie.service';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private readonly COOKIE_EXPIRATION_MINUTES = 30;
  private apiUrl = '/api/v1/auth'; // Proxied in dev, direct in prod

  constructor(
    private http: HttpClient,
    private cookieService: CookieService
  ) {}

  login(email: string, password: string): Observable<TokenResponse & { user: UserResponse }> {
    const loginData: LoginRequest = { email, password };
    return this.http.post<TokenResponse>(`${this.apiUrl}/login`, loginData).pipe(
      timeout(10000),
      retry(1),
      switchMap((tokenResponse: TokenResponse & { accessToken?: string; refreshToken?: string }) => {
        const accessToken = tokenResponse.accessToken || tokenResponse.access_token;
        const refreshToken = tokenResponse.refreshToken || tokenResponse.refresh_token;

        this.cookieService.set('access_token', accessToken, this.COOKIE_EXPIRATION_MINUTES);
        this.cookieService.set('refresh_token', refreshToken, this.COOKIE_EXPIRATION_MINUTES);

        return this.getCurrentUser(accessToken).pipe(
          map((user) => ({
            access_token: accessToken,
            refresh_token: refreshToken,
            token_type: 'bearer',
            user,
          })),
          catchError(() =>
            of({
              access_token: accessToken,
              refresh_token: refreshToken,
              token_type: 'bearer',
              user: { id: 0, email, first_name: 'User', last_name: '' } as UserResponse,
            })
          )
        );
      })
    );
  }

  register(email: string, password: string, firstName: string, lastName: string): Observable<UserResponse> {
    const registerData: RegisterRequest = { email, password, first_name: firstName, last_name: lastName };
    return this.http.post<UserResponse>(`${this.apiUrl}/register`, registerData).pipe(
      timeout(10000),
      retry(1),
    );
  }

  logout(): void {
    this.cookieService.remove('access_token');
    this.cookieService.remove('refresh_token');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
  }

  refreshToken(): Observable<TokenResponse> {
    const refreshToken = this.cookieService.get('refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }
    const refreshData: RefreshTokenRequest = { refresh_token: refreshToken };
    return this.http.post<TokenResponse>(`${this.apiUrl}/refresh`, refreshData).pipe(
      tap((tokenResponse) => {
        this.setTokens(tokenResponse.access_token, tokenResponse.refresh_token);
      })
    );
  }

  getCurrentUser(accessToken?: string): Observable<UserResponse> {
    const options = accessToken && accessToken.length > 50
      ? { headers: { Authorization: `Bearer ${accessToken}` } }
      : {};
    return this.http.get<UserResponse>(`${this.apiUrl}/me`, options).pipe(
      timeout(10000),
      retry(1),
    );
  }

  getAccessToken(): string | null {
    const token = this.cookieService.get('access_token')
      || localStorage.getItem('access_token')
      || sessionStorage.getItem('access_token');
    if (!token || token === 'undefined' || token === 'null' || token.length < 20) {
      return null;
    }
    return token;
  }

  setTokens(accessToken: string, refreshToken: string): void {
    this.cookieService.remove('access_token');
    this.cookieService.remove('refresh_token');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this.cookieService.set('access_token', accessToken, this.COOKIE_EXPIRATION_MINUTES);
    this.cookieService.set('refresh_token', refreshToken, this.COOKIE_EXPIRATION_MINUTES);
  }
}
```

## Règles NON-NÉGOCIABLES

1. Tokens stockés en cookies (expiration 30min) — jamais localStorage seul
2. `timeout(10000)` + `retry(1)` sur les appels réseau
3. Fallback si `getCurrentUser()` échoue après login
4. Validation du token (pas `undefined`, pas `null`, length > 20)
5. Cleanup complet dans `logout()` — cookies + localStorage + sessionStorage
6. Support des 2 formats (snake_case et camelCase) à cause de l'intercepteur
