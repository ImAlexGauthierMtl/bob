# Template: Pagination (Angular)

> Composant de pagination avec page size selector.

## Fichier à créer

`shared/components/pagination/pagination.component.ts`

```typescript
import { Component, Input, Output, EventEmitter, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

export interface PaginationEvent { page: number; pageSize: number; offset: number; }

@Component({
  selector: 'app-pagination',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="pagination">
      <span>{{ rangeStart }}–{{ rangeEnd }} sur {{ total }}</span>
      <div class="pagination__buttons">
        <button [disabled]="currentPage <= 1" (click)="goToPage(1)">«</button>
        <button [disabled]="currentPage <= 1" (click)="goToPage(currentPage - 1)">‹</button>
        @for (p of visiblePages; track p) {
          @if (p === '...') { <span>…</span> }
          @else { <button [class.active]="p === currentPage" (click)="goToPage(+p)">{{ p }}</button> }
        }
        <button [disabled]="currentPage >= totalPages" (click)="goToPage(currentPage + 1)">›</button>
        <button [disabled]="currentPage >= totalPages" (click)="goToPage(totalPages)">»</button>
      </div>
      <select [ngModel]="pageSize" (ngModelChange)="onPageSizeChange($event)">
        <option *ngFor="let s of pageSizeOptions" [ngValue]="s">{{ s }}</option>
      </select>
    </div>
  `,
  styleUrl: './pagination.component.scss',
})
export class PaginationComponent implements OnChanges {
  @Input() total = 0;
  @Input() pageSize = 50;
  @Input() currentPage = 1;
  @Input() pageSizeOptions = [50, 100, 200];
  @Output() pageChange = new EventEmitter<PaginationEvent>();

  totalPages = 1;
  visiblePages: (number | string)[] = [];

  get rangeStart() { return this.total === 0 ? 0 : (this.currentPage - 1) * this.pageSize + 1; }
  get rangeEnd() { return Math.min(this.currentPage * this.pageSize, this.total); }

  ngOnChanges() {
    this.totalPages = Math.max(1, Math.ceil(this.total / this.pageSize));
    this.visiblePages = this.buildPages();
  }

  goToPage(page: number) {
    if (page < 1 || page > this.totalPages || page === this.currentPage) return;
    this.currentPage = page;
    this.visiblePages = this.buildPages();
    this.emit();
  }

  onPageSizeChange(size: number) {
    this.pageSize = size; this.currentPage = 1;
    this.totalPages = Math.max(1, Math.ceil(this.total / this.pageSize));
    this.visiblePages = this.buildPages();
    this.emit();
  }

  private emit() {
    this.pageChange.emit({ page: this.currentPage, pageSize: this.pageSize, offset: (this.currentPage - 1) * this.pageSize });
  }

  private buildPages(): (number | string)[] {
    const t = this.totalPages, c = this.currentPage;
    if (t <= 7) return Array.from({ length: t }, (_, i) => i + 1);
    const p: (number | string)[] = [1];
    if (c > 3) p.push('...');
    for (let i = Math.max(2, c - 1); i <= Math.min(t - 1, c + 1); i++) p.push(i);
    if (c < t - 2) p.push('...');
    p.push(t);
    return p;
  }
}
```
