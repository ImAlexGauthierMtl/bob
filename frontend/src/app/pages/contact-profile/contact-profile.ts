import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { SlicePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ContactService } from '../../shared/services/contact.service';
import { OrganizationService } from '../../shared/services/organization.service';
import { ActivityService } from '../../shared/services/activity.service';
import { Contact } from '../../shared/models/contact.model';
import { Activity, CreateActivityDto } from '../../shared/models/activity.model';

@Component({
    selector: 'croo-contact-profile',
    standalone: true,
    imports: [RouterLink, SlicePipe, FormsModule],
    templateUrl: './contact-profile.html',
    styleUrl: './contact-profile.css',
})
export class ContactProfileComponent implements OnInit {
    contact: Contact | null = null;
    isLoading = true;
    activeTab = 'overview';
    orgName = '';
    activities: Activity[] = [];

    // Add Activity dialog
    showAddActivityDialog = false;
    newActivitySubject = '';
    newActivityDescription = '';
    newActivityType = 'TASK';
    newActivityPriority = 'MEDIUM';
    newActivityDueDate = '';
    isCreatingActivity = false;

    private route = inject(ActivatedRoute);
    private contactService = inject(ContactService);
    private orgService = inject(OrganizationService);
    private actService = inject(ActivityService);

    ngOnInit(): void {
        const id = this.route.snapshot.paramMap.get('id');
        if (id) {
            this.loadContact(id);
        }
    }

    loadContact(id: string): void {
        this.isLoading = true;
        this.contactService.getById(id).subscribe({
            next: (contact) => {
                this.contact = contact;
                this.isLoading = false;
                if (contact.organization_id) {
                    this.orgService.getById(contact.organization_id).subscribe({
                        next: (org) => this.orgName = org.name,
                    });
                }
                // Load activities linked to this contact
                this.actService.getAll(0, 50, undefined, id).subscribe({
                    next: (res) => this.activities = res.items,
                });
            },
            error: () => {
                this.isLoading = false;
            },
        });
    }

    setActiveTab(tab: string): void {
        this.activeTab = tab;
    }

    getInitials(): string {
        if (!this.contact) return '?';
        return `${this.contact.first_name[0]}${this.contact.last_name[0]}`.toUpperCase();
    }

    getStatusClass(status: string): string {
        switch (status) {
            case 'ACTIVE': return 'status-badge--accent';
            case 'LEAD': return 'status-badge--warn';
            case 'INACTIVE': return 'status-badge--muted';
            default: return 'status-badge--muted';
        }
    }

    // ── Add Activity Dialog ──────────────────────────

    openAddActivityDialog(): void {
        this.showAddActivityDialog = true;
        this.newActivitySubject = '';
        this.newActivityDescription = '';
        this.newActivityType = 'TASK';
        this.newActivityPriority = 'MEDIUM';
        this.newActivityDueDate = '';
        this.isCreatingActivity = false;
    }

    closeAddActivityDialog(): void {
        this.showAddActivityDialog = false;
    }

    createLinkedActivity(): void {
        if (!this.newActivitySubject.trim() || !this.contact) return;
        this.isCreatingActivity = true;

        const data: CreateActivityDto = {
            subject: this.newActivitySubject,
            description: this.newActivityDescription || undefined,
            activity_type: this.newActivityType,
            priority: this.newActivityPriority,
            contact_id: this.contact.id,
        };
        if (this.contact.organization_id) {
            data.organization_id = this.contact.organization_id;
        }
        if (this.newActivityDueDate) {
            data.due_date = this.newActivityDueDate;
        }

        this.actService.create(data).subscribe({
            next: () => {
                this.showAddActivityDialog = false;
                this.isCreatingActivity = false;
                // Refresh activities list
                this.actService.getAll(0, 50, undefined, this.contact!.id).subscribe({
                    next: (res) => this.activities = res.items,
                });
            },
            error: () => {
                this.isCreatingActivity = false;
            },
        });
    }
}
