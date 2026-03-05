# Template: Composant Dialog de Confirmation

> Recette pour créer un dialog de confirmation réutilisable.
> **Zéro décision** : composant standalone avec signal inputs/outputs.

## Fichier à créer

`frontend/src/app/components/confirm-dialog.component.ts`

## Code exact (copier tel quel)

```typescript
import { Component, input, output } from '@angular/core';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  template: `
    @if (open()) {
      <div class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/40" (click)="cancelClick.emit()"></div>
        <div class="relative bg-white rounded-sm shadow-xl max-w-md w-full mx-4 border border-gray-200">
          <div class="p-4 border-b border-gray-200 flex items-center justify-between">
            <h3 class="text-base font-bold text-gray-900">{{ title() }}</h3>
            <button (click)="cancelClick.emit()" class="text-gray-400 hover:text-gray-600">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          <div class="p-4">
            <div class="flex items-start gap-3">
              <div class="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                <i class="fa-solid fa-triangle-exclamation text-red-600 text-sm"></i>
              </div>
              <p class="text-sm text-gray-600">{{ message() }}</p>
            </div>
          </div>
          <div class="p-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-2">
            <button
              (click)="cancelClick.emit()"
              class="px-4 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors"
            >
              Annuler
            </button>
            <button
              (click)="confirmClick.emit()"
              class="px-4 py-1.5 text-sm font-medium text-white bg-red-600 rounded hover:bg-red-700 transition-colors"
            >
              <i class="fa-solid fa-trash-can mr-2"></i>
              {{ confirmLabel() }}
            </button>
          </div>
        </div>
      </div>
    }
  `,
})
export class ConfirmDialogComponent {
  open = input<boolean>(false);
  title = input<string>('Confirmation');
  message = input<string>('Êtes-vous sûr de vouloir continuer ?');
  confirmLabel = input<string>('Confirmer');

  confirmClick = output<void>();
  cancelClick = output<void>();
}
```

## Usage

```html
<app-confirm-dialog
  [open]="showDeleteDialog"
  title="Supprimer"
  [message]="'Supprimer ' + item.name + ' ?'"
  confirmLabel="Supprimer"
  (confirmClick)="onDelete()"
  (cancelClick)="showDeleteDialog = false"
/>
```

## Règles NON-NÉGOCIABLES

1. `input<T>(default)` — signal input avec défaut
2. `output<void>()` — signal output (pas @Output + EventEmitter)
3. Overlay = `fixed inset-0 z-50` + backdrop `bg-black/40`
4. Clic backdrop = cancel
5. Labels en français
