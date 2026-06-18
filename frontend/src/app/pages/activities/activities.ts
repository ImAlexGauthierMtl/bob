import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Store } from '@ngrx/store';
import { ActivityService } from '../../shared/services/activity.service';
import { Activity, CreateActivityDto } from '../../shared/models/activity.model';
import type { AppState } from '../../store';
import { loadCrmActivities } from '../../store/crm/crm.actions';
import {
    selectCrmActivities,
    selectCrmActivitiesLoading,
    selectCrmActivitiesTotal,
} from '../../store/crm/crm.selectors';

@Component({
    selector: 'croo-activities',
    standalone: true,
    imports: [RouterLink, DatePipe, FormsModule],
    templateUrl: './activities.html',
    styleUrl: './activities.css',
})
export class ActivitiesComponent implements OnInit {
    activeTypeFilter = 'ALL';
    searchQuery = '';

    // New Activity dialog
    showNewDialog = false;
    newActivity: CreateActivityDto = { subject: '' };
    isCreating = false;

    private store: Store<AppState> = inject(Store);
    private actService = inject(ActivityService);
    private activitiesSignal = this.store.selectSignal(selectCrmActivities);
    private totalSignal = this.store.selectSignal(selectCrmActivitiesTotal);
    private loadingSignal = this.store.selectSignal(selectCrmActivitiesLoading);

    get activities(): Activity[] {
        let items = this.activitiesSignal();
        if (this.activeTypeFilter !== 'ALL') {
            items = items.filter(a => a.activity_type === this.activeTypeFilter);
        }
        if (this.searchQuery.trim()) {
            const q = this.searchQuery.toLowerCase();
            items = items.filter(a =>
                a.subject.toLowerCase().includes(q) ||
                (a.description && a.description.toLowerCase().includes(q))
            );
        }
        return items;
    }

    get total(): number {
        return this.totalSignal();
    }

    get isLoading(): boolean {
        return this.loadingSignal();
    }

    ngOnInit(): void {
        this.loadActivities();
    }

    loadActivities(): void {
        this.store.dispatch(loadCrmActivities({ skip: 0, limit: 100 }));
    }

    setTypeFilter(type: string): void {
        this.activeTypeFilter = type;
        this.loadActivities();
    }

    onSearch(): void {
        this.loadActivities();
    }

    // ── New Activity Dialog ──────────────────────────

    openNewDialog(presetType?: string): void {
        this.newActivity = {
            subject: '',
            activity_type: presetType || 'TASK',
            priority: 'MEDIUM',
        };
        this.showNewDialog = true;
        this.isCreating = false;
    }

    closeNewDialog(): void {
        this.showNewDialog = false;
    }

    createActivity(): void {
        if (!this.newActivity.subject?.trim()) return;
        this.isCreating = true;
        this.actService.create(this.newActivity).subscribe({
            next: () => {
                this.showNewDialog = false;
                this.isCreating = false;
                this.loadActivities();
            },
            error: () => {
                this.isCreating = false;
            },
        });
    }

    // ── Helpers ──────────────────────────────────────

    getTypeIcon(type: string): string {
        switch (type) {
            case 'CALL': return 'fa-phone';
            case 'EMAIL': return 'fa-envelope';
            case 'MEETING': return 'fa-users';
            case 'TASK': return 'fa-check-circle';
            case 'NOTE': return 'fa-sticky-note';
            default: return 'fa-circle';
        }
    }

    getTypeColor(type: string): string {
        switch (type) {
            case 'CALL': return 'green';
            case 'EMAIL': return 'pink';
            case 'MEETING': return 'blue';
            case 'TASK': return 'purple';
            case 'NOTE': return 'yellow';
            default: return 'blue';
        }
    }

    getPriorityClass(priority: string): string {
        switch (priority) {
            case 'URGENT': return 'urgency-badge--red';
            case 'HIGH': return 'urgency-badge--orange';
            case 'MEDIUM': return 'urgency-badge--yellow';
            case 'LOW': return 'urgency-badge--muted';
            default: return 'urgency-badge--muted';
        }
    }

    getStatusClass(status: string): string {
        switch (status) {
            case 'COMPLETED': return 'type-badge--green';
            case 'IN_PROGRESS': return 'type-badge--blue';
            case 'CANCELLED': return 'type-badge--pink';
            case 'PENDING': return 'type-badge--purple';
            default: return 'type-badge--purple';
        }
    }
}
