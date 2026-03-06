import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DecimalPipe, UpperCasePipe } from '@angular/common';
import { OrganizationService, Organization, OrganizationProfile } from '../../shared/services/organization.service';
import { ContactService, Contact } from '../../shared/services/contact.service';
import { OpportunityService, Opportunity } from '../../shared/services/opportunity.service';
import { ActivityService, Activity } from '../../shared/services/activity.service';

@Component({
    selector: 'croo-organization-detail',
    standalone: true,
    imports: [RouterLink, UpperCasePipe, DecimalPipe],
    templateUrl: './organization-detail.html',
    styleUrl: './organization-detail.css',
})
export class OrganizationDetailComponent implements OnInit {
    org: Organization | null = null;
    contacts: Contact[] = [];
    opportunities: Opportunity[] = [];
    activities: Activity[] = [];
    isLoading = true;
    isEnriching = false;
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
}
