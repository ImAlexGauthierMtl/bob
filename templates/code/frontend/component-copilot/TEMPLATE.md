# Template: Copilot Sidebar (Angular)

> Sidebar contextuelle pour assistant IA avec onglets actions/tâches.

## Fichier

`components/copilot-sidebar/copilot-sidebar.component.ts`

```typescript
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

interface CopilotAction { icon: string; title: string; description: string; }
interface CopilotTask { title: string; description: string; priority?: string; date?: string; type: 'task' | 'automation'; }

@Component({
  selector: 'app-copilot-sidebar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <aside class="copilot" [class.copilot--collapsed]="isCollapsed">
      <div class="copilot__header">
        <h3><i class="fa-solid fa-robot"></i> Copilot</h3>
        <button (click)="toggleCollapse()"><i [class]="isCollapsed ? 'fa-solid fa-expand' : 'fa-solid fa-compress'"></i></button>
      </div>

      @if (!isCollapsed) {
        <div class="copilot__tabs">
          <button [class.active]="activeTab === 'actions'" (click)="setActiveTab('actions')">Actions</button>
          <button [class.active]="activeTab === 'tasks'" (click)="setActiveTab('tasks')">Tâches</button>
        </div>

        <div class="copilot__content">
          @if (activeTab === 'actions') {
            @for (action of recommendedActions; track action.title) {
              <div class="copilot__card">
                <i [class]="action.icon"></i>
                <div><strong>{{ action.title }}</strong><p>{{ action.description }}</p></div>
              </div>
            }
          }
          @if (activeTab === 'tasks') {
            @for (task of tasks; track task.title) {
              <div class="copilot__card">
                <span class="copilot__priority" *ngIf="task.priority">{{ task.priority }}</span>
                <div><strong>{{ task.title }}</strong><p>{{ task.description }}</p></div>
              </div>
            }
          }
        </div>
      }
    </aside>
  `,
  styleUrl: './copilot-sidebar.component.scss',
})
export class CopilotSidebarComponent {
  activeTab = 'actions';
  isCollapsed = false;

  @Input() recommendedActions: CopilotAction[] = [];
  @Input() tasks: CopilotTask[] = [];

  setActiveTab(tab: string) { this.activeTab = tab; }
  toggleCollapse() { this.isCollapsed = !this.isCollapsed; }
}
```
