# Template: Page Login (Angular)

> Recette pour créer la page de connexion avec formulaire réactif.
> **Zéro décision** : suivre exactement ce pattern.

## Fichier à créer

`pages/public/login/login.component.ts`

```typescript
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { Store } from '@ngrx/store';
import { AuthActions } from '../../../store/auth/auth.actions';
import { selectAuthError, selectAuthLoading } from '../../../store/auth/auth.selectors';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <form [formGroup]="loginForm" (ngSubmit)="onSubmit()">
      <h2>Connexion</h2>

      <div class="form-group">
        <label for="email">Email</label>
        <input
          id="email"
          type="email"
          formControlName="email"
          placeholder="votre@email.com"
          [class.invalid]="loginForm.get('email')?.invalid && loginForm.get('email')?.touched"
        />
        @if (loginForm.get('email')?.errors?.['required'] && loginForm.get('email')?.touched) {
          <span class="error">L'email est requis</span>
        }
        @if (loginForm.get('email')?.errors?.['email'] && loginForm.get('email')?.touched) {
          <span class="error">Format d'email invalide</span>
        }
      </div>

      <div class="form-group">
        <label for="password">Mot de passe</label>
        <input
          id="password"
          type="password"
          formControlName="password"
          placeholder="••••••••"
          [class.invalid]="loginForm.get('password')?.invalid && loginForm.get('password')?.touched"
        />
        @if (loginForm.get('password')?.errors?.['required'] && loginForm.get('password')?.touched) {
          <span class="error">Le mot de passe est requis</span>
        }
      </div>

      @if (error$ | async; as error) {
        <div class="alert alert--error">{{ error }}</div>
      }

      <button
        type="submit"
        [disabled]="loginForm.invalid || (loading$ | async)"
        class="btn btn--primary btn--full"
      >
        @if (loading$ | async) {
          <span class="spinner"></span> Connexion...
        } @else {
          Se connecter
        }
      </button>
    </form>
  `,
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  loginForm: FormGroup;
  error$ = this.store.select(selectAuthError);
  loading$ = this.store.select(selectAuthLoading);

  constructor(
    private fb: FormBuilder,
    private store: Store,
    private router: Router
  ) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required]],
    });
  }

  onSubmit(): void {
    if (this.loginForm.invalid) return;
    const { email, password } = this.loginForm.value;
    this.store.dispatch(AuthActions.login({ email, password }));
  }
}
```

## `pages/public/login/login.component.scss`

```scss
form {
  display: flex;
  flex-direction: column;
  gap: 20px;

  h2 {
    text-align: center;
    font-size: 20px;
    font-weight: 600;
    margin-bottom: 8px;
  }
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;

  label {
    font-size: 14px;
    font-weight: 500;
    color: #333;
  }

  input {
    padding: 10px 14px;
    border: 1px solid #ddd;
    border-radius: 8px;
    font-size: 14px;
    transition: border-color 0.2s;

    &:focus {
      outline: none;
      border-color: var(--primary, #4f46e5);
      box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
    }

    &.invalid {
      border-color: #ef4444;
    }
  }
}

.error {
  font-size: 12px;
  color: #ef4444;
}

.alert {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;

  &--error {
    background: #fef2f2;
    color: #dc2626;
    border: 1px solid #fecaca;
  }
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &--primary {
    background: var(--primary, #4f46e5);
    color: white;

    &:hover:not(:disabled) {
      background: var(--primary-dark, #4338ca);
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }

  &--full {
    width: 100%;
  }
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

## Règles NON-NÉGOCIABLES

1. `ReactiveFormsModule` — jamais template-driven forms
2. Validation : `Validators.required` + `Validators.email`
3. Dispatch NgRx action `AuthActions.login()` — pas d'appel HTTP direct
4. Loading state + error state depuis le store
5. Bouton disabled pendant le loading
6. Messages d'erreur affichés uniquement après `touched`
