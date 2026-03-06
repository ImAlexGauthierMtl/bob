import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { SlicePipe } from '@angular/common';
import { ContactService, Contact } from '../../shared/services/contact.service';
import { OrganizationService } from '../../shared/services/organization.service';

@Component({
    selector: 'croo-contact-profile',
    standalone: true,
    imports: [RouterLink, SlicePipe],
    templateUrl: './contact-profile.html',
    styleUrl: './contact-profile.css',
})
export class ContactProfileComponent implements OnInit {
    contact: Contact | null = null;
    isLoading = true;
    activeTab = 'overview';
    orgName = '';

    constructor(
        private route: ActivatedRoute,
        private contactService: ContactService,
        private orgService: OrganizationService,
    ) { }

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
}
