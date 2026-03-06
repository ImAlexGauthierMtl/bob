# Template: Page Détail avec Onglets (Angular)

> Recette pour créer une page de détail d'une ressource avec onglets.
> **Zéro décision** : suivre exactement ce pattern.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom (PascalCase) | `Opportunity` |
| `resource` | Nom (kebab-case) | `opportunity` |
| `TABS` | Liste des onglets | `['Général', 'Produits', 'Activités']` |

## Fichier à créer

`features/{resources}/{resource}-detail/{resource}-detail.component.ts`

```typescript
import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';

import { Store } from '@ngrx/store';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { {Resource}Actions } from '../../../store/{resources}/{resources}.actions';
import { select{Resource}ById, select{Resources}Loading } from '../../../store/{resources}/{resources}.selectors';

@Component({
  selector: 'app-{resource}-detail',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="detail-page">
      <!-- Header -->
      <div class="detail-page__header">
        <button class="btn btn--ghost" (click)="goBack()">
          ← Retour
        </button>
        <div class="detail-page__title">
          @if (loading$ | async) {
            <div class="skeleton skeleton--title"></div>
          } @else if ({resource}$ | async; as item) {
            <h1>{{ item.name }}</h1>
            <span class="badge">{{ item.status }}</span>
          }
        </div>
        <div class="detail-page__actions">
          <button class="btn btn--secondary" (click)="onEdit()">Modifier</button>
          <button class="btn btn--danger" (click)="onDelete()">Supprimer</button>
        </div>
      </div>

      <!-- Tabs -->
      <div class="detail-page__tabs">
        @for (tab of tabs; track tab.id) {
          <button
            class="tab"
            [class.tab--active]="activeTab === tab.id"
            (click)="activeTab = tab.id"
          >
            {{ tab.label }}
          </button>
        }
      </div>

      <!-- Tab content -->
      <div class="detail-page__content">
        @switch (activeTab) {
          @case ('general') {
            <div class="tab-content">
              <!-- Informations générales -->
              @if ({resource}$ | async; as item) {
                <div class="info-grid">
                  <div class="info-card">
                    <label>Nom</label>
                    <p>{{ item.name }}</p>
                  </div>
                  <!-- Ajouter les champs ici -->
                  <div class="info-card">
                    <label>Créé le</label>
                    <p>{{ item.createdAt | date:'dd/MM/yyyy HH:mm' }}</p>
                  </div>
                  <div class="info-card">
                    <label>Mis à jour le</label>
                    <p>{{ item.updatedAt | date:'dd/MM/yyyy HH:mm' }}</p>
                  </div>
                </div>
              }
            </div>
          }
          @case ('activities') {
            <div class="tab-content">
              <p>Activités à implémenter</p>
            </div>
          }
        }
      </div>
    </div>
  `,
  styleUrl: './{resource}-detail.component.scss',
})
export class {Resource}DetailComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  private {resource}Id: string = '';

  {resource}$ = this.store.select(select{Resource}ById);
  loading$ = this.store.select(select{Resources}Loading);

  activeTab = 'general';
  tabs = [
    { id: 'general', label: 'Général' },
    { id: 'activities', label: 'Activités' },
    // Ajouter d'autres onglets
  ];

  constructor(
    private store: Store,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.route.params
      .pipe(takeUntil(this.destroy$))
      .subscribe((params) => {
        this.{resource}Id = params['id'];
        this.store.dispatch({Resource}Actions.loadById({ id: this.{resource}Id }));
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  goBack(): void {
    this.router.navigate(['/admin/{resources}']);
  }

  onEdit(): void {
    this.router.navigate(['/admin/{resources}', this.{resource}Id, 'edit']);
  }

  onDelete(): void {
    if (confirm('Êtes-vous sûr de vouloir supprimer ?')) {
      this.store.dispatch({Resource}Actions.delete({ id: this.{resource}Id }));
    }
  }
}
```

## SCSS

```scss
.detail-page {
  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
    gap: 16px;
  }

  &__title {
    flex: 1;
    h1 { font-size: 24px; font-weight: 700; margin: 0; }
  }

  &__actions {
    display: flex;
    gap: 8px;
  }

  &__tabs {
    display: flex;
    border-bottom: 2px solid #e5e7eb;
    margin-bottom: 24px;
    gap: 0;
  }

  &__content {
    min-height: 400px;
  }
}

.tab {
  padding: 10px 20px;
  border: none;
  background: none;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;

  &--active {
    color: var(--primary, #4f46e5);
    border-bottom-color: var(--primary, #4f46e5);
  }

  &:hover:not(&--active) {
    color: #374151;
  }
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.info-card {
  padding: 16px;
  border-radius: 8px;
  background: white;
  border: 1px solid #e5e7eb;

  label {
    font-size: 12px;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  p {
    font-size: 15px;
    margin: 4px 0 0;
    color: #111827;
  }
}

.skeleton {
  background: linear-gradient(90deg, #e5e7eb 25%, #f3f4f6 50%, #e5e7eb 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;

  &--title { width: 240px; height: 32px; }
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

## Règles NON-NÉGOCIABLES

1. Charger la ressource via le store NgRx — ID depuis `ActivatedRoute.params`
2. `OnDestroy` avec `Subject` pour cleanup des subscriptions
3. Onglets dynamiques avec `@switch`
4. Skeleton loading pendant le chargement
5. Bouton retour, modifier, supprimer dans le header
6. Grid responsive pour les info cards
