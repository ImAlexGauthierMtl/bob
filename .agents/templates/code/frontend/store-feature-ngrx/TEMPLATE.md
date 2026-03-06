# Template: Store NgRx Feature (Angular)

> Store NgRx complet pour un feature module avec auth.

## Fichiers à créer (5 fichiers)

### `store/auth/auth.actions.ts`

```typescript
import { createAction, props } from '@ngrx/store';
import { UserResponse } from '../../core/models/auth.models';

export const AuthActions = {
  login: createAction('[Auth] Login', props<{ email: string; password: string }>()),
  loginSuccess: createAction('[Auth] Login Success', props<{ user: UserResponse | null; accessToken: string; refreshToken: string }>()),
  loginFailure: createAction('[Auth] Login Failure', props<{ error: string }>()),
  register: createAction('[Auth] Register', props<{ email: string; password: string; firstName: string; lastName: string }>()),
  registerSuccess: createAction('[Auth] Register Success', props<{ user: UserResponse }>()),
  registerFailure: createAction('[Auth] Register Failure', props<{ error: string }>()),
  logout: createAction('[Auth] Logout'),
  refreshToken: createAction('[Auth] Refresh Token'),
  refreshTokenSuccess: createAction('[Auth] Refresh Token Success', props<{ accessToken: string; refreshToken: string }>()),
  refreshTokenFailure: createAction('[Auth] Refresh Token Failure', props<{ error: string }>()),
  getCurrentUser: createAction('[Auth] Get Current User'),
  getCurrentUserSuccess: createAction('[Auth] Get Current User Success', props<{ user: UserResponse }>()),
  getCurrentUserFailure: createAction('[Auth] Get Current User Failure', props<{ error: string }>()),
};
```

### `store/auth/auth.reducer.ts`

```typescript
import { createReducer, on } from '@ngrx/store';
import { UserResponse } from '../../core/models/auth.models';
import { AuthActions } from './auth.actions';

export interface AuthState {
  user: UserResponse | null;
  accessToken: string | null;
  refreshToken: string | null;
  loading: boolean;
  error: string | null;
}

const initialState: AuthState = { user: null, accessToken: null, refreshToken: null, loading: false, error: null };

export const authReducer = createReducer(initialState,
  on(AuthActions.login, (s) => ({ ...s, loading: true, error: null })),
  on(AuthActions.loginSuccess, (s, { user, accessToken, refreshToken }) => ({ ...s, user, accessToken, refreshToken, loading: false, error: null })),
  on(AuthActions.loginFailure, (s, { error }) => ({ ...s, loading: false, error, accessToken: null, refreshToken: null })),
  on(AuthActions.logout, () => ({ ...initialState })),
  on(AuthActions.refreshTokenSuccess, (s, { accessToken, refreshToken }) => ({ ...s, accessToken, refreshToken, loading: false })),
  on(AuthActions.getCurrentUserSuccess, (s, { user }) => ({ ...s, user, loading: false })),
);
```

### `store/auth/auth.selectors.ts`

```typescript
import { createFeatureSelector, createSelector } from '@ngrx/store';
import { AuthState } from './auth.reducer';

export const selectAuthState = createFeatureSelector<AuthState>('auth');
export const selectUser = createSelector(selectAuthState, (s) => s.user);
export const selectAccessToken = createSelector(selectAuthState, (s) => s.accessToken);
export const selectIsAuthenticated = createSelector(selectAuthState, (s) => !!s.accessToken);
export const selectAuthLoading = createSelector(selectAuthState, (s) => s.loading);
export const selectAuthError = createSelector(selectAuthState, (s) => s.error);
```

### `store/auth/auth.effects.ts`

```typescript
import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { of } from 'rxjs';
import { catchError, map, switchMap, tap } from 'rxjs/operators';
import { AuthActions } from './auth.actions';
import { AuthService } from '../../core/services/auth.service';

@Injectable()
export class AuthEffects {
  private actions$ = inject(Actions);
  private authService = inject(AuthService);
  private router = inject(Router);

  login$ = createEffect(() => this.actions$.pipe(
    ofType(AuthActions.login),
    switchMap(({ email, password }) => this.authService.login(email, password).pipe(
      map((res) => AuthActions.loginSuccess({ user: res.user, accessToken: res.access_token, refreshToken: res.refresh_token })),
      catchError((err) => of(AuthActions.loginFailure({ error: err.error?.detail || 'Erreur de connexion' })))
    ))
  ));

  loginSuccess$ = createEffect(() => this.actions$.pipe(
    ofType(AuthActions.loginSuccess),
    tap(({ accessToken, refreshToken }) => {
      this.authService.setTokens(accessToken, refreshToken);
      this.router.navigate(['/admin/dashboard']);
    })
  ), { dispatch: false });

  logout$ = createEffect(() => this.actions$.pipe(
    ofType(AuthActions.logout),
    tap(() => { this.authService.logout(); this.router.navigate(['/auth/login']); })
  ), { dispatch: false });
}
```

### Enregistrement dans `app.config.ts`

```typescript
import { provideStore } from '@ngrx/store';
import { provideEffects } from '@ngrx/effects';
import { authReducer } from './store/auth/auth.reducer';
import { AuthEffects } from './store/auth/auth.effects';

providers: [
  provideStore({ auth: authReducer }),
  provideEffects([AuthEffects]),
]
```
