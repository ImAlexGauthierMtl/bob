# Template: Page Dashboard (Angular)

> Page d'accueil avec grille de stat cards.

## Fichier

`features/dashboard/dashboard.component.ts`

```typescript
import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Store } from '@ngrx/store';
import { StatCardComponent } from '../../shared/components/stat-card/stat-card.component';
import { selectUser } from '../../store/auth/auth.selectors';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, StatCardComponent],
  template: `
    <div class="dashboard">
      <div class="dashboard__header">
        <h1>Dashboard</h1>
        <p>Bienvenue{{ (user$ | async)?.firstName ? ', ' + (user$ | async)?.firstName : '' }}</p>
      </div>

      <div class="dashboard__stats">
        @for (stat of stats; track stat.title) {
          <app-stat-card
            [title]="stat.title"
            [subtitle]="stat.subtitle"
            [value]="stat.value"
            [icon]="stat.icon"
            [iconBg]="stat.iconBg"
            [iconColor]="stat.iconColor"
          />
        }
      </div>

      <div class="dashboard__grid">
        <div class="dashboard__card">
          <h3>Activité récente</h3>
          <!-- Contenu à implémenter -->
        </div>
        <div class="dashboard__card">
          <h3>Actions rapides</h3>
          <!-- Contenu à implémenter -->
        </div>
      </div>
    </div>
  `,
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit {
  private store = inject(Store);
  user$ = this.store.select(selectUser);

  stats = [
    { title: 'Clients', subtitle: 'Total actifs', value: '—', icon: 'fa-solid fa-users', iconBg: '#e0e7ff', iconColor: '#4f46e5' },
    { title: 'Revenus', subtitle: 'Ce mois', value: '—', icon: 'fa-solid fa-dollar-sign', iconBg: '#d1fae5', iconColor: '#059669' },
    { title: 'Tâches', subtitle: 'En cours', value: '—', icon: 'fa-solid fa-list-check', iconBg: '#fef3c7', iconColor: '#d97706' },
  ];

  ngOnInit(): void {
    // Charger les données du dashboard
  }
}
```

## SCSS

```scss
.dashboard {
  &__header { margin-bottom: 24px; h1 { font-size: 24px; font-weight: 700; } p { color: #6b7280; } }
  &__stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; margin-bottom: 24px; }
  &__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 16px; }
  &__card { background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; h3 { font-size: 16px; font-weight: 600; margin-bottom: 12px; } }
}
```
