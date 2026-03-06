import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ContactService, Contact } from '../../shared/services/contact.service';

@Component({
    selector: 'croo-contacts',
    standalone: true,
    imports: [RouterLink],
    templateUrl: './contacts.html',
    styleUrl: './contacts.css',
})
export class ContactsComponent implements OnInit {
    contacts: Contact[] = [];
    total = 0;
    isLoading = true;

    constructor(private contactService: ContactService) { }

    ngOnInit(): void {
        this.loadContacts();
    }

    loadContacts(): void {
        this.isLoading = true;
        this.contactService.list().subscribe({
            next: (res) => {
                this.contacts = res.items;
                this.total = res.total;
                this.isLoading = false;
            },
            error: () => (this.isLoading = false),
        });
    }

    getInitials(c: Contact): string {
        return `${c.first_name[0]}${c.last_name[0]}`.toUpperCase();
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
