import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ActivityService } from '../../shared/services/activity.service';
import { Activity } from '../../shared/models/activity.model';

@Component({
    selector: 'croo-activities',
    standalone: true,
    imports: [RouterLink],
    templateUrl: './activities.html',
    styleUrl: './activities.css',
})
export class ActivitiesComponent implements OnInit {
    activities: Activity[] = [];
    total = 0;
    isLoading = true;

    private actService = inject(ActivityService);

    ngOnInit(): void {
        this.loadActivities();
    }

    loadActivities(): void {
        this.isLoading = true;
        this.actService.getAll().subscribe({
            next: (res) => {
                this.activities = res.items;
                this.total = res.total;
                this.isLoading = false;
            },
            error: () => (this.isLoading = false),
        });
    }

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

    getPriorityClass(priority: string): string {
        switch (priority) {
            case 'URGENT': return 'status-badge--danger';
            case 'HIGH': return 'status-badge--warn';
            case 'MEDIUM': return 'status-badge--muted';
            case 'LOW': return 'status-badge--muted';
            default: return 'status-badge--muted';
        }
    }

    getStatusClass(status: string): string {
        switch (status) {
            case 'COMPLETED': return 'status-badge--accent';
            case 'IN_PROGRESS': return 'status-badge--warn';
            case 'CANCELLED': return 'status-badge--danger';
            default: return 'status-badge--muted';
        }
    }
}
