# Template: Toolbar (Angular)

> Barre d'outils avec boutons d'actions configurables.

## Fichier

`shared/components/toolbar/toolbar.component.ts`

```typescript
import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface ActionButton {
  icon: string; label: string; action: () => void; primary?: boolean; divider?: boolean;
}

@Component({
  selector: 'app-toolbar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="toolbar">
      <div class="toolbar__search" *ngIf="showSearch">
        <i class="fa-solid fa-search"></i>
        <input type="text" [placeholder]="searchPlaceholder" (input)="onSearch($event)" />
      </div>
      <div class="toolbar__actions">
        @for (btn of buttons; track btn.label) {
          @if (btn.divider) { <div class="toolbar__divider"></div> }
          <button [class.primary]="btn.primary" (click)="btn.action()">
            <i [class]="btn.icon"></i> {{ btn.label }}
          </button>
        }
      </div>
    </div>
  `,
  styleUrl: './toolbar.component.scss',
})
export class ToolbarComponent {
  @Input() buttons: ActionButton[] = [];
  @Input() showSearch = true;
  @Input() searchPlaceholder = 'Rechercher...';
  @Output() search = new EventEmitter<string>();

  private debounceTimer: any;

  onSearch(event: Event) {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      this.search.emit((event.target as HTMLInputElement).value);
    }, 300);
  }
}
```
