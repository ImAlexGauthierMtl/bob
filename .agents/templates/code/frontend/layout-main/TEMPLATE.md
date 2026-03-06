# Template: Layout Principal (Angular)

> Recette pour créer le shell layout avec header, sidebar et content area.
> **Zéro décision** : suivre exactement ce pattern.

## Fichiers à créer (4 composants)

### 1. `layout/main-layout/main-layout.component.ts`

```typescript
import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HeaderComponent } from '../header/header.component';
import { SidebarComponent } from '../sidebar/sidebar.component';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [RouterOutlet, HeaderComponent, SidebarComponent],
  template: `
    <div class="layout">
      <app-sidebar
        [collapsed]="sidebarCollapsed"
        (toggle)="toggleSidebar()"
      />
      <div class="layout__main" [class.layout__main--expanded]="sidebarCollapsed">
        <app-header (toggleSidebar)="toggleSidebar()" />
        <main class="layout__content">
          <router-outlet />
        </main>
      </div>
    </div>
  `,
  styleUrl: './main-layout.component.scss',
})
export class MainLayoutComponent {
  sidebarCollapsed = false;

  toggleSidebar(): void {
    this.sidebarCollapsed = !this.sidebarCollapsed;
  }
}
```

### 2. `layout/main-layout/main-layout.component.scss`

```scss
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;

  &__main {
    flex: 1;
    display: flex;
    flex-direction: column;
    transition: margin-left 0.3s ease;
    margin-left: 260px;

    &--expanded {
      margin-left: 64px;
    }
  }

  &__content {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    background-color: var(--bg-secondary, #f5f5f5);
  }
}
```

### 3. `layout/auth-layout/auth-layout.component.ts`

```typescript
import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-auth-layout',
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <div class="auth-layout">
      <div class="auth-layout__card">
        <div class="auth-layout__logo">
          <h1>{PROJECT_NAME}</h1>
        </div>
        <router-outlet />
      </div>
    </div>
  `,
  styleUrl: './auth-layout.component.scss',
})
export class AuthLayoutComponent {}
```

### 4. `layout/auth-layout/auth-layout.component.scss`

```scss
.auth-layout {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, var(--primary, #1a1a2e) 0%, var(--primary-dark, #16213e) 100%);

  &__card {
    width: 100%;
    max-width: 420px;
    padding: 40px;
    border-radius: 12px;
    background: white;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  }

  &__logo {
    text-align: center;
    margin-bottom: 32px;

    h1 {
      font-size: 24px;
      font-weight: 700;
      color: var(--primary);
    }
  }
}
```

## Routing setup — `app.routes.ts`

```typescript
import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { guestGuard } from './core/guards/guest.guard';

export const routes: Routes = [
  {
    path: 'auth',
    loadComponent: () =>
      import('./layout/auth-layout/auth-layout.component').then((m) => m.AuthLayoutComponent),
    canActivate: [guestGuard],
    children: [
      { path: 'login', loadComponent: () => import('./pages/public/login/login.component').then((m) => m.LoginComponent) },
      { path: '', redirectTo: 'login', pathMatch: 'full' },
    ],
  },
  {
    path: 'admin',
    loadComponent: () =>
      import('./layout/main-layout/main-layout.component').then((m) => m.MainLayoutComponent),
    canActivate: [authGuard],
    children: [
      { path: 'dashboard', loadComponent: () => import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent) },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
    ],
  },
  { path: '', redirectTo: '/admin/dashboard', pathMatch: 'full' },
  { path: '**', redirectTo: '/admin/dashboard' },
];
```

## Règles NON-NÉGOCIABLES

1. Standalone components — pas de NgModules
2. Lazy loading via `loadComponent` — jamais d'import direct
3. Auth layout pour `/auth/*`, Main layout pour `/admin/*`
4. Sidebar collapsible avec animation CSS transition
5. `router-outlet` dans chaque layout
6. Guards sur les routes : `authGuard` sur admin, `guestGuard` sur auth
