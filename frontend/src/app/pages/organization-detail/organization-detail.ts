import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { OrganizationService, Organization } from '../../shared/services/organization.service';
import { ContactService, Contact } from '../../shared/services/contact.service';
import { OpportunityService, Opportunity } from '../../shared/services/opportunity.service';
import { ActivityService, Activity } from '../../shared/services/activity.service';

@Component({
    selector: 'croo-organization-detail',
    standalone: true,
    imports: [RouterLink],
    templateUrl: './organization-detail.html',
    styleUrl: './organization-detail.css',
})
export class OrganizationDetailComponent implements OnInit {
    org: Organization | null = null;
    contacts: Contact[] = [];
    opportunities: Opportunity[] = [];
    activities: Activity[] = [];
    isLoading = true;
    activeTab = 'overview';

    constructor(
        private route: ActivatedRoute,
        private orgService: OrganizationService,
        private contactService: ContactService,
        private oppService: OpportunityService,
        private actService: ActivityService,
    ) { }

    ngOnInit(): void {
        const id = this.route.snapshot.paramMap.get('id');
        if (id) {
            this.loadOrganization(id);
        }
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
            },
        });
    }

    loadRelated(orgId: string): void {
        this.contactService.list(0, 10, orgId).subscribe({
            next: (res) => (this.contacts = res.items),
        });
        this.oppService.list(0, 10, orgId).subscribe({
            next: (res) => (this.opportunities = res.items),
        });
        this.actService.list(0, 10, orgId).subscribe({
            next: (res) => (this.activities = res.items),
        });
    }

    pollEnrichment(id: string): void {
        const interval = setInterval(() => {
            this.orgService.getById(id).subscribe({
                next: (org) => {
                    this.org = org;
                    if (org.ai_enriched === 'Y') {
                        clearInterval(interval);
                    }
                },
            });
        }, 5000);
        // Stop polling after 2 min
        setTimeout(() => clearInterval(interval), 120_000);
    }

    setActiveTab(tab: string): void {
        this.activeTab = tab;
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
}
