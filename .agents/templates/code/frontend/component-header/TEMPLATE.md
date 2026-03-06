# Template: Header Applicatif (Angular)

> Barre de navigation supérieure avec toggle sidebar, user menu, logout.

## Fichier à créer

`layout/header/header.component.ts`

```typescript
import { Component, ChangeDetectionStrategy, output, inject, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Store } from '@ngrx/store';
import { logout } from '../../store/auth/auth.actions';
import { selectUser } from '../../store/auth/auth.selectors';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="header">
      <button class="header__menu-btn" (click)="onToggleSidebar()">
        <i class="fa-solid fa-bars"></i>
      </button>

      <div class="header__spacer"></div>

      <div class="user-menu-container">
        <button class="header__user" (click)="toggleUserMenu()">
          <div class="header__avatar">{{ userInitials }}</div>
          <span class="header__username">{{ userName }}</span>
          <i class="fa-solid fa-chevron-down"></i>
        </button>
        @if (userMenuOpen) {
          <div class="header__dropdown">
            <a class="header__dropdown-item" (click)="onLogout()">
              <i class="fa-solid fa-right-from-bracket"></i> Déconnexion
            </a>
          </div>
        }
      </div>
    </header>
  `,
  styleUrl: './header.component.scss',
})
export class HeaderComponent {
  private store = inject(Store);
  toggleSidebar = output<void>();

  user$ = this.store.select(selectUser);
  userInitials = 'U';
  userName = 'Utilisateur';
  userMenuOpen = false;

  onToggleSidebar(): void { this.toggleSidebar.emit(); }
  toggleUserMenu(): void { this.userMenuOpen = !this.userMenuOpen; }
  onLogout(): void { this.userMenuOpen = false; this.store.dispatch(logout()); }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!(event.target as HTMLElement).closest('.user-menu-container')) {
      this.userMenuOpen = false;
    }
  }
}
```

## SCSS

```scss
.header {
  height: 56px; display: flex; align-items: center; padding: 0 16px;
  background: white; border-bottom: 1px solid #e5e7eb; gap: 12px;

  &__menu-btn { background: none; border: none; font-size: 18px; cursor: pointer; color: #6b7280; padding: 8px; }
  &__spacer { flex: 1; }
  &__user { display: flex; align-items: center; gap: 8px; background: none; border: none; cursor: pointer; }
  &__avatar { width: 32px; height: 32px; border-radius: 50%; background: var(--primary, #4f46e5); color: white; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }
  &__username { font-size: 14px; font-weight: 500; }
  &__dropdown { position: absolute; right: 16px; top: 48px; background: white; border: 1px solid #e5e7eb; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); min-width: 180px; z-index: 50; }
  &__dropdown-item { display: flex; align-items: center; gap: 8px; padding: 10px 16px; cursor: pointer; font-size: 14px; color: #374151; &:hover { background: #f3f4f6; } }
}
.user-menu-container { position: relative; }
```
