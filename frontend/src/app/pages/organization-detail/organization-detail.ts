import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { DecimalPipe, UpperCasePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { OrganizationService } from '../../shared/services/organization.service';
import { ContactService } from '../../shared/services/contact.service';
import { OpportunityService } from '../../shared/services/opportunity.service';
import { ActivityService } from '../../shared/services/activity.service';
import { BobActionService } from '../../shared/services/bob-action.service';
import { Organization, OrganizationProfile } from '../../shared/models/organization.model';
import { Contact, CreateContactDto } from '../../shared/models/contact.model';
import { Opportunity, CreateOpportunityDto } from '../../shared/models/opportunity.model';
import { Activity, CreateActivityDto } from '../../shared/models/activity.model';

@Component({
    selector: 'croo-organization-detail',
    standalone: true,
    imports: [RouterLink, UpperCasePipe, DecimalPipe, FormsModule],
    templateUrl: './organization-detail.html',
    styleUrl: './organization-detail.css',
})
export class OrganizationDetailComponent implements OnInit, OnDestroy {
    org: Organization | null = null;
    contacts: Contact[] = [];
    opportunities: Opportunity[] = [];
    activities: Activity[] = [];
    isLoading = true;
    notFound = false;
    isEnriching = false;
    activeTab = 'overview';

    // Add Contact dialog
    showAddContactDialog = false;
    contactInput = '';
    isProcessingContact = false;
    isCreatingContact = false;
    contactStatusMessage = '';
    parsedContactPreview: Partial<CreateContactDto> | null = null;

    // Add Opportunity dialog
    showAddOppDialog = false;
    oppInput = '';
    isProcessingOpp = false;
    isCreatingOpp = false;
    oppStatusMessage = '';
    parsedOppPreview: Partial<CreateOpportunityDto> | null = null;

    // Add Activity dialog
    showAddActivityDialog = false;
    newActivitySubject = '';
    newActivityDescription = '';
    newActivityType = 'TASK';
    newActivityPriority = 'MEDIUM';
    newActivityDueDate = '';
    isCreatingActivity = false;

    private bobActionSub?: Subscription;

    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private orgService = inject(OrganizationService);
    private contactService = inject(ContactService);
    private oppService = inject(OpportunityService);
    private actService = inject(ActivityService);
    private bobAction = inject(BobActionService);

    ngOnInit(): void {
        const id = this.route.snapshot.paramMap.get('id');
        if (id) {
            this.loadOrganization(id);
        }

        this.bobActionSub = this.bobAction.action$.subscribe(action => {
            if (action.type === 'ui_switch_tab' && action.name) {
                const validTabs = ['overview', 'profile', 'contacts', 'opportunities', 'activities'];
                // Clean the tab name given by LLM
                let targetTab = action.name.toLowerCase().trim();

                // Try to find a match (e.g. if the user says "activity", map it to "activities")
                const matchedTab = validTabs.find(t => t.includes(targetTab) || targetTab.includes(t));

                if (matchedTab) {
                    this.setActiveTab(matchedTab);
                }
            }
        });
    }

    ngOnDestroy(): void {
        this.bobActionSub?.unsubscribe();
    }

    loadOrganization(id: string): void {
        this.isLoading = true;
        this.orgService.getById(id).subscribe({
            next: (org) => {
                this.org = org;
                this.isLoading = false;
                this.loadRelated(id);
                // If enrichment is pending, poll until done
                if (org.ai_enriched !== 'Y') {
                    this.pollEnrichment(id);
                }
            },
            error: () => {
                this.isLoading = false;
                this.notFound = true;
            },
        });
    }

    loadRelated(orgId: string): void {
        this.contactService.getAll(0, 10, orgId).subscribe({
            next: (res) => (this.contacts = res.items),
        });
        this.oppService.getAll(0, 10, orgId).subscribe({
            next: (res) => (this.opportunities = res.items),
        });
        this.actService.getAll(0, 10, orgId).subscribe({
            next: (res) => (this.activities = res.items),
        });
    }

    pollEnrichment(id: string): void {
        const interval = setInterval(() => {
            this.orgService.getById(id).subscribe({
                next: (org) => {
                    this.org = org;
                    // Check if profile is populated (not just ai_enriched)
                    if (org.organization_profile && this.hasProfileData(org.organization_profile)) {
                        clearInterval(interval);
                        this.isEnriching = false;
                    }
                },
            });
        }, 5000);
        // Stop polling after 2 min
        setTimeout(() => {
            clearInterval(interval);
            this.isEnriching = false;
        }, 120_000);
    }

    setActiveTab(tab: string): void {
        this.activeTab = tab;
    }

    goBack(): void {
        this.router.navigate(['/organizations']);
    }

    getInitials(name: string): string {
        return name.split(' ').map((w) => w[0]).join('').substring(0, 2).toUpperCase();
    }

    formatRevenue(revenue: number | null): string {
        if (!revenue) return '—';
        if (revenue >= 1_000_000_000) return `$${(revenue / 1_000_000_000).toFixed(1)}B`;
        if (revenue >= 1_000_000) return `$${(revenue / 1_000_000).toFixed(1)}M`;
        if (revenue >= 1_000) return `$${(revenue / 1_000).toFixed(0)}K`;
        return `$${revenue}`;
    }

    getWinRate(): number {
        if (!this.opportunities || this.opportunities.length === 0) return 0;
        const won = this.opportunities.filter(o => o.stage === 'CLOSED_WON').length;
        return (won / this.opportunities.length) * 100;
    }

    triggerEnrichment(): void {
        if (!this.org || this.isEnriching) return;
        this.isEnriching = true;
        this.orgService.enrich(this.org.id).subscribe({
            next: () => {
                // Start polling for enrichment completion
                this.pollEnrichment(this.org!.id);
            },
            error: () => {
                this.isEnriching = false;
            },
        });
    }

    getFullAddress(): string {
        if (!this.org) return '—';
        const parts = [
            this.org.address_street,
            this.org.address_city,
            this.org.address_state,
            this.org.address_postal_code,
            this.org.address_country,
        ].filter(Boolean);
        return parts.length ? parts.join(', ') : '—';
    }

    hasProfileData(profile: OrganizationProfile): boolean {
        if (!profile) return false;
        return !!(
            profile.company_info ||
            profile.contact_info ||
            profile.social_media ||
            (profile.key_people && profile.key_people.length) ||
            (profile.services_products && profile.services_products.length) ||
            profile.business_details
        );
    }

    formatProfileAddress(address: { street?: string; city?: string; state?: string; country?: string; postal_code?: string }): string {
        const parts = [
            address.street,
            address.city,
            address.state,
            address.postal_code,
            address.country,
        ].filter(Boolean);
        return parts.join(', ') || '—';
    }

    // ── Add Contact Dialog ──────────────────────────────

    openAddContactDialog(): void {
        this.showAddContactDialog = true;
        this.contactInput = '';
        this.isProcessingContact = false;
        this.isCreatingContact = false;
        this.contactStatusMessage = '';
        this.parsedContactPreview = null;
    }

    closeAddContactDialog(): void {
        this.showAddContactDialog = false;
    }

    processContactInput(): void {
        if (!this.contactInput.trim()) return;
        this.isProcessingContact = true;
        this.contactStatusMessage = '';
        this.parsedContactPreview = null;

        this.contactService.bobParse(this.contactInput, this.org?.id).subscribe({
            next: (result) => {
                this.parsedContactPreview = result.extracted;
                this.isProcessingContact = false;
                this.contactStatusMessage = `Bob extracted fields (${Math.round(result.confidence * 100)}% confidence)`;
            },
            error: () => {
                this.isProcessingContact = false;
                this.contactStatusMessage = '❌ Bob could not parse the text. Try rephrasing.';
            },
        });
    }

    createContactFromParsed(): void {
        if (!this.parsedContactPreview?.first_name || !this.parsedContactPreview?.last_name || !this.org) return;
        this.isCreatingContact = true;

        const data: CreateContactDto = {
            first_name: this.parsedContactPreview.first_name,
            last_name: this.parsedContactPreview.last_name,
            email: this.parsedContactPreview.email,
            phone: this.parsedContactPreview.phone,
            job_title: this.parsedContactPreview.job_title,
            department: this.parsedContactPreview.department,
            organization_id: this.org.id,
            status: 'ACTIVE',
        };

        this.contactService.create(data).subscribe({
            next: () => {
                this.showAddContactDialog = false;
                // Refresh contacts list
                this.contactService.getAll(0, 10, this.org!.id).subscribe({
                    next: (res) => (this.contacts = res.items),
                });
            },
            error: () => {
                this.isCreatingContact = false;
                this.contactStatusMessage = '❌ Failed to create contact.';
            },
        });
    }




    // ── Add Opportunity Dialog ───────────────────────────

    openAddOppDialog(): void {
        this.showAddOppDialog = true;
        this.oppInput = '';
        this.isProcessingOpp = false;
        this.isCreatingOpp = false;
        this.oppStatusMessage = '';
        this.parsedOppPreview = null;
    }

    closeAddOppDialog(): void {
        this.showAddOppDialog = false;
    }

    processOppInput(): void {
        if (!this.oppInput.trim()) return;
        this.isProcessingOpp = true;
        this.oppStatusMessage = '';
        this.parsedOppPreview = null;

        setTimeout(() => {
            this.parsedOppPreview = this.parseOppText(this.oppInput);
            this.isProcessingOpp = false;
        }, 600);
    }

    createOppFromParsed(): void {
        if (!this.parsedOppPreview?.name || !this.org) return;
        this.isCreatingOpp = true;

        const data: CreateOpportunityDto = {
            name: this.parsedOppPreview.name,
            description: this.parsedOppPreview.description,
            stage: this.parsedOppPreview.stage || 'PROSPECTING',
            priority: this.parsedOppPreview.priority || 'MEDIUM',
            amount: this.parsedOppPreview.amount,
            probability: this.parsedOppPreview.probability,
            close_date: this.parsedOppPreview.close_date,
            source: this.parsedOppPreview.source,
            organization_id: this.org.id,
        };

        this.oppService.create(data).subscribe({
            next: () => {
                this.showAddOppDialog = false;
                this.oppService.getAll(0, 10, this.org!.id).subscribe({
                    next: (res) => (this.opportunities = res.items),
                });
            },
            error: () => {
                this.isCreatingOpp = false;
                this.oppStatusMessage = '❌ Failed to create opportunity.';
            },
        });
    }

    private parseOppText(text: string): Partial<CreateOpportunityDto> {
        const result: Partial<CreateOpportunityDto> = {};

        // Extract dollar amounts
        const amountMatch = text.match(/\$([\d,]+(?:\.\d{1,2})?)\s*([KkMm])?/);
        if (amountMatch) {
            let amount = parseFloat(amountMatch[1].replace(/,/g, ''));
            const suffix = amountMatch[2]?.toUpperCase();
            if (suffix === 'K') amount *= 1_000;
            if (suffix === 'M') amount *= 1_000_000;
            result.amount = amount;
            text = text.replace(amountMatch[0], '');
        }

        // Extract probability
        const probMatch = text.match(/(\d{1,3})\s*%/);
        if (probMatch) {
            result.probability = parseInt(probMatch[1], 10);
            text = text.replace(probMatch[0], '');
        }

        // Extract stage keywords
        const stageMap: Record<string, string> = {
            'prospecting': 'PROSPECTING', 'prospect': 'PROSPECTING',
            'qualification': 'QUALIFICATION', 'qualified': 'QUALIFICATION',
            'proposal': 'PROPOSAL', 'negotiation': 'NEGOTIATION', 'negotiate': 'NEGOTIATION',
            'closed won': 'CLOSED_WON', 'won': 'CLOSED_WON',
            'closed lost': 'CLOSED_LOST', 'lost': 'CLOSED_LOST',
        };
        for (const [keyword, stage] of Object.entries(stageMap)) {
            if (text.toLowerCase().includes(keyword)) {
                result.stage = stage;
                text = text.replace(new RegExp(keyword, 'gi'), '');
                break;
            }
        }

        // Extract priority
        const priorityMap: Record<string, string> = {
            'high priority': 'HIGH', 'high': 'HIGH', 'urgent': 'HIGH',
            'low priority': 'LOW', 'low': 'LOW',
            'medium': 'MEDIUM', 'normal': 'MEDIUM',
        };
        for (const [keyword, priority] of Object.entries(priorityMap)) {
            if (text.toLowerCase().includes(keyword)) {
                result.priority = priority;
                text = text.replace(new RegExp(keyword, 'gi'), '');
                break;
            }
        }

        // Clean and use remaining as name
        text = text.replace(/[,;|·•—–]+/g, ' ').replace(/\s+/g, ' ').trim();
        if (text) {
            result.name = text;
        } else {
            result.name = 'New Opportunity';
        }

        return result;
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
        if (!this.newActivitySubject.trim() || !this.org) return;
        this.isCreatingActivity = true;

        const data: CreateActivityDto = {
            subject: this.newActivitySubject,
            description: this.newActivityDescription || undefined,
            activity_type: this.newActivityType,
            priority: this.newActivityPriority,
            organization_ids: [this.org.id],
        };
        if (this.newActivityDueDate) {
            data.due_date = this.newActivityDueDate;
        }

        this.actService.create(data).subscribe({
            next: () => {
                this.showAddActivityDialog = false;
                this.isCreatingActivity = false;
                // Refresh activities list
                this.actService.getAll(0, 10, this.org!.id).subscribe({
                    next: (res) => (this.activities = res.items),
                });
            },
            error: () => {
                this.isCreatingActivity = false;
            },
        });
    }
}
