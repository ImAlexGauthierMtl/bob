# Template: Data Table réutilisable (Angular)

> Table de données avec tri, sélection, templates de colonnes.

## Fichier à créer

`shared/components/data-table/data-table.component.ts`

```typescript
import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface TableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  template?: 'text' | 'link' | 'badge' | 'currency' | 'date';
}

@Component({
  selector: 'app-data-table',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th *ngIf="selectable"><input type="checkbox" [checked]="allSelected" (change)="onSelectAll($event)" /></th>
            <th *ngFor="let col of columns" (click)="col.sortable !== false && onSort(col.key)">
              {{ col.label }}
              <i *ngIf="col.sortable !== false" class="sort-icon"></i>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let row of data" (click)="rowClick.emit(row)" class="row-hover">
            <td *ngIf="selectable"><input type="checkbox" [checked]="isSelected(row)" (click)="$event.stopPropagation()" (change)="onRowSelect(row)" /></td>
            <td *ngFor="let col of columns">
              <ng-container [ngSwitch]="col.template || 'text'">
                <span *ngSwitchCase="'badge'" class="badge">{{ getValue(row, col.key) }}</span>
                <span *ngSwitchCase="'currency'">{{ getValue(row, col.key) | currency:'USD' }}</span>
                <span *ngSwitchDefault>{{ getValue(row, col.key) }}</span>
              </ng-container>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  `,
  styleUrl: './data-table.component.scss',
})
export class DataTableComponent {
  @Input() columns: TableColumn[] = [];
  @Input() data: any[] = [];
  @Input() selectable = false;
  @Output() rowClick = new EventEmitter<any>();
  @Output() sort = new EventEmitter<string>();
  @Output() selectionChange = new EventEmitter<any[]>();

  selectedRows = new Set<any>();
  allSelected = false;

  getValue(obj: any, path: string): any {
    return path.split('.').reduce((acc, part) => acc?.[part], obj);
  }

  onSort(key: string) { this.sort.emit(key); }

  onRowSelect(row: any) {
    this.selectedRows.has(row) ? this.selectedRows.delete(row) : this.selectedRows.add(row);
    this.allSelected = this.data.length > 0 && this.selectedRows.size === this.data.length;
    this.selectionChange.emit(Array.from(this.selectedRows));
  }

  onSelectAll(event: any) {
    event.target.checked ? this.data.forEach(r => this.selectedRows.add(r)) : this.selectedRows.clear();
    this.allSelected = event.target.checked;
    this.selectionChange.emit(Array.from(this.selectedRows));
  }

  isSelected(row: any): boolean { return this.selectedRows.has(row); }
}
```
