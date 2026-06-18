import { Component, OnInit, OnDestroy, effect, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Store } from '@ngrx/store';
import { Subscription } from 'rxjs';
import { ContactService } from '../../shared/services/contact.service';
import { OrganizationService } from '../../shared/services/organization.service';
import { BobActionService } from '../../shared/services/bob-action.service';
import { Contact, CreateContactDto } from '../../shared/models/contact.model';
import type { AppState } from '../../store';
import { loadCrmContacts } from '../../store/crm/crm.actions';
import {
    selectCrmContacts,
    selectCrmContactsLoading,
    selectCrmContactsTotal,
} from '../../store/crm/crm.selectors';

@Component({
    selector: 'croo-contacts',
    standalone: true,
    imports: [RouterLink, FormsModule],
    templateUrl: './contacts.html',
    styleUrl: './contacts.css',
})
export class ContactsComponent implements OnInit, OnDestroy {
    // Pagination
    currentPage = 1;
    pageSize = 50;
    Math = Math;

    // Dialog state
    showAddDialog = false;
    contactInput = '';
    isProcessing = false;
    isCreating = false;
    statusMessage = '';
    statusType: 'info' | 'success' | 'error' = 'info';

    // Parsed preview
    parsedPreview: Partial<CreateContactDto> | null = null;

    // Org name resolution
    orgNames: Record<string, string> = {};

    private bobActionSub?: Subscription;

    private store: Store<AppState> = inject(Store);
    private contactService = inject(ContactService);
    private orgService = inject(OrganizationService);
    private router = inject(Router);
    private bobActionService = inject(BobActionService);
    private contactsSignal = this.store.selectSignal(selectCrmContacts);
    private totalSignal = this.store.selectSignal(selectCrmContactsTotal);
    private loadingSignal = this.store.selectSignal(selectCrmContactsLoading);
    private orgNameEffect = effect(() => this.resolveOrgNames(this.contactsSignal()));

    get contacts(): Contact[] {
        return this.contactsSignal();
    }

    get total(): number {
        return this.totalSignal();
    }

    get isLoading(): boolean {
        return this.loadingSignal();
    }

    get totalPages(): number {
        return Math.max(1, Math.ceil(this.total / this.pageSize));
    }

    ngOnInit(): void {
        this.loadContacts();

        // Listen for Bob voice actions
        this.bobActionSub = this.bobActionService.action$.subscribe(action => {
            if (action.type === 'open_create_dialog' && action.entity === 'contact') {
                this.openAddDialog();
            } else if (action.type === 'ui_update_input' && this.showAddDialog) {
                if (action.text !== undefined) {
                    this.contactInput = action.text;
                }
                if (action.submit) {
                    this.processInput();
                }
            } else if (action.type === 'ui_select_result' && this.showAddDialog) {
                if (action.index === 1 && this.parsedPreview) {
                    this.createFromParsed();
                }
            }
        });
    }

    ngOnDestroy(): void {
        this.bobActionSub?.unsubscribe();
    }

    loadContacts(): void {
        const skip = (this.currentPage - 1) * this.pageSize;
        this.store.dispatch(loadCrmContacts({ skip, limit: this.pageSize }));
    }

    goToPage(page: number): void {
        if (page < 1 || page > this.totalPages) return;
        this.currentPage = page;
        this.loadContacts();
    }

    onPageSizeChange(event: Event): void {
        this.pageSize = +(event.target as HTMLSelectElement).value;
        this.currentPage = 1;
        this.loadContacts();
    }

    getPages(): number[] {
        const pages: number[] = [];
        const max = Math.min(this.totalPages, 5);
        let start = Math.max(1, this.currentPage - Math.floor(max / 2));
        const end = Math.min(this.totalPages, start + max - 1);
        start = Math.max(1, end - max + 1);
        for (let i = start; i <= end; i++) pages.push(i);
        return pages;
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

        const data: CreateContactDto = {
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

    private resolveOrgNames(contacts: Contact[]): void {
        const orgIds = [...new Set(
            contacts.map(c => c.organization_id).filter((id): id is string => !!id && !this.orgNames[id])
        )];
        for (const id of orgIds) {
            this.orgService.getById(id).subscribe({
                next: (org) => this.orgNames[id] = org.name,
            });
        }
    }
}
