# Template: Stat Card (Angular)

> Carte de métrique pour dashboard.

## Fichier

`shared/components/stat-card/stat-card.component.ts`

```typescript
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-stat-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="stat-card">
      <div class="stat-card__header">
        <div class="stat-card__icon" [style.background]="iconBg">
          <i [class]="icon" [style.color]="iconColor"></i>
        </div>
        <span class="stat-card__value">{{ value }}</span>
      </div>
      <h3 class="stat-card__title">{{ title }}</h3>
      <p class="stat-card__subtitle" *ngIf="subtitle">{{ subtitle }}</p>
    </div>
  `,
  styleUrl: './stat-card.component.scss',
})
export class StatCardComponent {
  @Input() title = '';
  @Input() subtitle = '';
  @Input() value: string | number = '';
  @Input() icon = 'fa-solid fa-chart-bar';
  @Input() iconBg = '#e0e7ff';
  @Input() iconColor = '#4f46e5';
}
```

## SCSS

```scss
.stat-card {
  background: white; border: 1px solid #e5e7eb; border-radius: 12px;
  padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);

  &__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  &__icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; i { font-size: 20px; } }
  &__value { font-size: 28px; font-weight: 700; color: #111827; }
  &__title { font-size: 14px; font-weight: 600; color: #374151; }
  &__subtitle { font-size: 12px; color: #6b7280; margin-top: 4px; }
}
```
