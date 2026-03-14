import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { SlicePipe, DatePipe, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ContactService } from '../../shared/services/contact.service';
import { OrganizationService } from '../../shared/services/organization.service';
import { ActivityService } from '../../shared/services/activity.service';
import { MS365Service } from '../../shared/services/ms365.service';
import { ClientMapService } from '../../shared/services/client-map.service';
import { Contact } from '../../shared/models/contact.model';
import { Activity, CreateActivityDto } from '../../shared/models/activity.model';
import { SyncedEmail } from '../../shared/models/ms365.model';
import { ClientMap, GoldenNote, CreateGoldenNote, EMOTIONAL_CLIMATE_ICONS, DISC_LABELS } from '../../shared/models/client-map.model';

@Component({
    selector: 'croo-contact-profile',
    standalone: true,
    imports: [RouterLink, SlicePipe, DatePipe, DecimalPipe, FormsModule],
    templateUrl: './contact-profile.html',
    styleUrl: './contact-profile.css',
})
export class ContactProfileComponent implements OnInit {
    contact: Contact | null = null;
    isLoading = true;
    activeTab = 'overview';
    orgName = '';
    activities: Activity[] = [];
    contactEmails: SyncedEmail[] = [];

    // Client Map 360°
    clientMap: ClientMap | null = null;
    isLoadingClientMap = false;
    isSavingClientMap = false;
    editingQuadrant: string | null = null;
    showGoldenNoteForm = false;
    isAnalyzingBehavior = false;
    newNote: CreateGoldenNote = {
        interaction_date: new Date().toISOString().slice(0, 16),
        interaction_type: 'CALL',
    };
    emotionalIcons = EMOTIONAL_CLIMATE_ICONS;
    discLabels = DISC_LABELS;

    // Add Activity dialog
    showAddActivityDialog = false;
    newActivitySubject = '';
    newActivityDescription = '';
    newActivityType = 'TASK';
    newActivityPriority = 'MEDIUM';
    newActivityDueDate = '';
    isCreatingActivity = false;

    // Bob's Rolodex
    isEnrichingLinkedIn = false;

    private route = inject(ActivatedRoute);
    private contactService = inject(ContactService);
    private orgService = inject(OrganizationService);
    private actService = inject(ActivityService);
    private ms365Service = inject(MS365Service);
    private clientMapService = inject(ClientMapService);

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
                // Load real emails linked to this contact (from/to/cc via junction)
                this.ms365Service.getEmails(0, 50, undefined, undefined, undefined, id).subscribe({
                    next: (res) => this.contactEmails = res.items,
                });
            },
            error: () => {
                this.isLoading = false;
            },
        });
    }

    setActiveTab(tab: string): void {
        this.activeTab = tab;
        if (tab === 'client-map' && !this.clientMap && this.contact) {
            this.loadClientMap(this.contact.id);
        }
    }

    // ── Client Map 360° ──────────────────────────────

    loadClientMap(contactId: string): void {
        this.isLoadingClientMap = true;
        this.clientMapService.getByContactId(contactId).subscribe({
            next: (cm) => {
                this.clientMap = cm;
                this.isLoadingClientMap = false;
            },
            error: () => {
                this.clientMap = null;
                this.isLoadingClientMap = false;
            },
        });
    }

    saveQuadrant(): void {
        if (!this.contact || !this.clientMap) return;
        this.isSavingClientMap = true;
        this.clientMapService.upsert(this.contact.id, this.clientMap).subscribe({
            next: (cm) => {
                this.clientMap = cm;
                this.isSavingClientMap = false;
                this.editingQuadrant = null;
            },
            error: () => this.isSavingClientMap = false,
        });
    }

    initClientMap(): void {
        if (!this.contact) return;
        this.isSavingClientMap = true;
        this.clientMapService.upsert(this.contact.id, {}).subscribe({
            next: (cm) => {
                this.clientMap = cm;
                this.isSavingClientMap = false;
            },
            error: () => this.isSavingClientMap = false,
        });
    }

    addGoldenNote(): void {
        if (!this.contact) return;
        this.clientMapService.addGoldenNote(this.contact.id, this.newNote).subscribe({
            next: (note) => {
                if (this.clientMap) this.clientMap.golden_notes.unshift(note);
                this.showGoldenNoteForm = false;
                this.newNote = { interaction_date: new Date().toISOString().slice(0, 16), interaction_type: 'CALL' };
            },
        });
    }

    deleteGoldenNote(noteId: string): void {
        if (!this.contact || !this.clientMap) return;
        this.clientMapService.deleteGoldenNote(this.contact.id, noteId).subscribe({
            next: () => {
                if (this.clientMap) {
                    this.clientMap.golden_notes = this.clientMap.golden_notes.filter(n => n.id !== noteId);
                }
            },
        });
    }

    triggerBehaviorAnalysis(): void {
        if (!this.contact) return;
        this.isAnalyzingBehavior = true;
        this.clientMapService.analyzeBehavior(this.contact.id).subscribe({
            next: (res) => {
                if (this.clientMap) this.clientMap.behavioral_profile = res.behavioral_profile;
                this.isAnalyzingBehavior = false;
            },
            error: () => this.isAnalyzingBehavior = false,
        });
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
            contact_ids: [this.contact.id],
        };
        if (this.contact.organization_id) {
            data.organization_ids = [this.contact.organization_id];
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

    // ── Bob's Rolodex (Bright Data) ─────────────────

    triggerLinkedInEnrichment(): void {
        if (!this.contact || this.isEnrichingLinkedIn) return;

        const linkedinUrl = this.contact.linkedin_url || this.contact.contact_profile?.linkedin;
        if (!linkedinUrl) {
            alert('No LinkedIn URL on this contact. Add a LinkedIn URL first.');
            return;
        }

        this.isEnrichingLinkedIn = true;
        this.contactService.enrichLinkedIn(this.contact.id).subscribe({
            next: () => {
                // Poll for completion after 5s
                setTimeout(() => {
                    this.loadContact(this.contact!.id);
                    this.isEnrichingLinkedIn = false;
                }, 5000);
            },
            error: () => {
                this.isEnrichingLinkedIn = false;
                alert('Enrichment failed. Check that the contact has a valid LinkedIn URL.');
            },
        });
    }
}
