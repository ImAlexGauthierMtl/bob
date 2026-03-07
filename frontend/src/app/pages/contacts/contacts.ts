import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ContactService, Contact, CreateContactRequest } from '../../shared/services/contact.service';
import { OrganizationService } from '../../shared/services/organization.service';
import { BobActionService } from '../../shared/services/bob-action.service';
import { Subscription } from 'rxjs';

@Component({
    selector: 'croo-contacts',
    standalone: true,
    imports: [RouterLink, FormsModule],
    templateUrl: './contacts.html',
    styleUrl: './contacts.css',
})
export class ContactsComponent implements OnInit, OnDestroy {
    contacts: Contact[] = [];
    total = 0;
    isLoading = true;

    // Dialog state
    showAddDialog = false;
    contactInput = '';
    isProcessing = false;
    isCreating = false;
    statusMessage = '';
    statusType: 'info' | 'success' | 'error' = 'info';

    // Parsed preview
    parsedPreview: Partial<CreateContactRequest> | null = null;

    // Org name resolution
    orgNames: Record<string, string> = {};

    private bobActionSub?: Subscription;

    constructor(
        private contactService: ContactService,
        private orgService: OrganizationService,
        private router: Router,
        private bobActionService: BobActionService,
    ) { }

    ngOnInit(): void {
        this.loadContacts();

        // Listen for Bob voice actions
        this.bobActionSub = this.bobActionService.action$.subscribe(action => {
            if (action.type === 'open_create_dialog' && action.entity === 'contact') {
                this.openAddDialog();
            }
        });
    }

    ngOnDestroy(): void {
        this.bobActionSub?.unsubscribe();
    }

    loadContacts(): void {
        this.isLoading = true;
        this.contactService.list().subscribe({
            next: (res) => {
                this.contacts = res.items;
                this.total = res.total;
                this.isLoading = false;
                this.resolveOrgNames();
            },
            error: () => (this.isLoading = false),
        });
    }

    // ── Dialog ──────────────────────────────

    openAddDialog(): void {
        this.showAddDialog = true;
        this.resetDialog();
    }

    closeAddDialog(): void {
        this.showAddDialog = false;
    }

    resetDialog(): void {
        this.contactInput = '';
        this.isProcessing = false;
        this.isCreating = false;
        this.statusMessage = '';
        this.parsedPreview = null;
    }

    // ── AI Agent Processing ─────────────────

    processInput(): void {
        if (!this.contactInput.trim()) return;
        this.isProcessing = true;
        this.statusMessage = '';
        this.parsedPreview = null;

        this.contactService.aiParse(this.contactInput).subscribe({
            next: (result) => {
                this.parsedPreview = result.extracted;
                this.isProcessing = false;
                this.statusMessage = `Bob extracted fields (${Math.round(result.confidence * 100)}% confidence)`;
                this.statusType = 'success';
            },
            error: () => {
                this.isProcessing = false;
                this.statusMessage = '❌ Bob could not parse the text. Try rephrasing.';
                this.statusType = 'error';
            },
        });
    }

    createFromParsed(): void {
        if (!this.parsedPreview || !this.parsedPreview.first_name || !this.parsedPreview.last_name) return;
        this.isCreating = true;

        const data: CreateContactRequest = {
            first_name: this.parsedPreview.first_name,
            last_name: this.parsedPreview.last_name,
            email: this.parsedPreview.email,
            phone: this.parsedPreview.phone,
            job_title: this.parsedPreview.job_title,
            department: this.parsedPreview.department,
            status: 'ACTIVE',
        };

        this.contactService.create(data).subscribe({
            next: (contact) => {
                this.showAddDialog = false;
                this.router.navigate(['/contacts', contact.id]);
            },
            error: () => {
                this.isCreating = false;
                this.statusMessage = '❌ Failed to create contact.';
                this.statusType = 'error';
            },
        });
    }



    // ── Helpers ──────────────────────────────

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

    private resolveOrgNames(): void {
        const orgIds = [...new Set(
            this.contacts.map(c => c.organization_id).filter((id): id is string => !!id)
        )];
        for (const id of orgIds) {
            this.orgService.getById(id).subscribe({
                next: (org) => this.orgNames[id] = org.name,
            });
        }
    }
}
