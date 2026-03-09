import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivityService } from '../../shared/services/activity.service';
import { Activity, CreateActivityDto } from '../../shared/models/activity.model';

@Component({
    selector: 'croo-activities',
    standalone: true,
    imports: [RouterLink, DatePipe, FormsModule],
    templateUrl: './activities.html',
    styleUrl: './activities.css',
})
export class ActivitiesComponent implements OnInit {
    activities: Activity[] = [];
    total = 0;
    isLoading = true;
    activeTypeFilter = 'ALL';
    searchQuery = '';

    // New Activity dialog
    showNewDialog = false;
    newActivity: CreateActivityDto = { subject: '' };
    isCreating = false;

    private actService = inject(ActivityService);

    ngOnInit(): void {
        this.loadActivities();
    }

    loadActivities(): void {
        this.isLoading = true;
        const typeFilter = this.activeTypeFilter !== 'ALL' ? this.activeTypeFilter : undefined;
        this.actService.getAll(0, 100, undefined, undefined, undefined, undefined).subscribe({
            next: (res) => {
                let items = res.items;
                // Client-side type filter
                if (typeFilter) {
                    items = items.filter(a => a.activity_type === typeFilter);
                }
                // Client-side search
                if (this.searchQuery.trim()) {
                    const q = this.searchQuery.toLowerCase();
                    items = items.filter(a =>
                        a.subject.toLowerCase().includes(q) ||
                        (a.description && a.description.toLowerCase().includes(q))
                    );
                }
                this.activities = items;
                this.total = res.total;
                this.isLoading = false;
            },
            error: () => (this.isLoading = false),
        });
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
