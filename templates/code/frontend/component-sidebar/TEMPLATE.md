# Template: Sidebar de Navigation (Angular)

> Sidebar collapsible avec menu items dynamiques.

## Fichier à créer

`layout/sidebar/sidebar.component.ts`

```typescript
import { CommonModule } from '@angular/common';
import { Component, ChangeDetectionStrategy, output, input, inject } from '@angular/core';
import { RouterModule, Router } from '@angular/router';

export interface MenuItem {
  id: string;
  label: string;
  icon: string;
  route: string;
  children?: MenuItem[];
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <aside class="sidebar" [class.sidebar--collapsed]="collapsed()">
      <div class="sidebar__logo">
        @if (!collapsed()) { <h2>{PROJECT_NAME}</h2> }
        @else { <span>P</span> }
      </div>

      <nav class="sidebar__nav">
        @for (item of menuItems; track item.id) {
          <a
            class="sidebar__item"
            [routerLink]="item.route"
            routerLinkActive="sidebar__item--active"
            [title]="item.label"
            (click)="navigate(item)"
          >
            <i [class]="item.icon"></i>
            @if (!collapsed()) { <span>{{ item.label }}</span> }
          </a>
        }
      </nav>

      <div class="sidebar__footer">
        <button class="sidebar__toggle" (click)="onToggle()">
          <i [class]="collapsed() ? 'fa-solid fa-angles-right' : 'fa-solid fa-angles-left'"></i>
        </button>
      </div>
    </aside>
  `,
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent {
  collapsed = input<boolean>(false);
  toggle = output<void>();

  private router = inject(Router);

  menuItems: MenuItem[] = [
    { id: 'dashboard', label: 'Dashboard', icon: 'fa-solid fa-gauge', route: '/admin/dashboard' },
    // Ajouter les items ici
  ];

  navigate(item: MenuItem): void {
    this.router.navigate([item.route]);
  }

  onToggle(): void {
    this.toggle.emit();
  }
}
```

## SCSS

```scss
.sidebar {
  width: 260px; height: 100vh; position: fixed; left: 0; top: 0;
  background: var(--sidebar-bg, #1a1a2e); color: white;
  display: flex; flex-direction: column; transition: width 0.3s ease; z-index: 100;

  &--collapsed { width: 64px; }

  &__logo { padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); h2 { font-size: 18px; } }
  &__nav { flex: 1; overflow-y: auto; padding: 8px; }

  &__item {
    display: flex; align-items: center; gap: 12px; padding: 10px 12px;
    border-radius: 8px; color: rgba(255,255,255,0.7); text-decoration: none;
    transition: all 0.2s; font-size: 14px;
    &:hover { background: rgba(255,255,255,0.1); color: white; }
    &--active { background: rgba(255,255,255,0.15); color: white; font-weight: 600; }
    i { width: 20px; text-align: center; }
  }

  &__footer { padding: 12px; border-top: 1px solid rgba(255,255,255,0.1); }
  &__toggle { background: none; border: none; color: rgba(255,255,255,0.5); cursor: pointer; padding: 8px; width: 100%; }
}
```
