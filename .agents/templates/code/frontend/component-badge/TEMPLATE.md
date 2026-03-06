# Template: Composant Badge de Statut

> Recette pour créer un badge qui affiche un statut avec couleur et icône.
> **Zéro décision** : signal input, computed pour label/couleur/icône.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `StatusType` | Type union des statuts | `ReviewStatus` |
| `VALUES` | Valeurs avec labels FR | `NEW → Nouveau, ACTIVE → Actif` |

## Fichier à créer

`frontend/src/app/components/{resource}-status-badge.component.ts`

## Code exact

```typescript
import { Component, input, computed } from '@angular/core';
import { {StatusType} } from '../models/{resource}.model';

@Component({
  selector: 'app-{resource}-status-badge',
  standalone: true,
  template: `
    <span [class]="badgeClasses()">
      <i [class]="iconClass()"></i>
      {{ label() }}
    </span>
  `,
})
export class {Resource}StatusBadgeComponent {
  status = input.required<{StatusType}>();

  label = computed(() => {
    const labels: Record<{StatusType}, string> = {
      // Remplir avec les labels français
    };
    return labels[this.status()] ?? this.status();
  });

  iconClass = computed(() => {
    const icons: Record<{StatusType}, string> = {
      // fa-solid fa-circle, fa-spinner, fa-check, etc.
    };
    return icons[this.status()] ?? 'fa-solid fa-circle text-[6px] mr-1.5';
  });

  badgeClasses = computed(() => {
    const base = 'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border';
    const colors: Record<{StatusType}, string> = {
      // bg-{color}-50 text-{color}-700 border-{color}-200
    };
    return `${base} ${colors[this.status()] ?? 'bg-gray-100 text-gray-600 border-gray-200'}`;
  });
}
```

## Règles NON-NÉGOCIABLES

1. `input.required<T>()` — signal input, pas @Input()
2. `computed()` — pas de méthodes appelées depuis le template
3. Badges = `bg-{color}-50 text-{color}-700 border-{color}-200` (pattern Tailwind)
4. Icônes = Font Awesome 6 solid
5. Labels en français
