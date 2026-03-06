import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { OrganizationService, Organization, EnrichmentResult } from '../../shared/services/organization.service';

@Component({
    selector: 'croo-organizations',
    standalone: true,
    imports: [RouterLink, FormsModule],
    templateUrl: './organizations.html',
    styleUrl: './organizations.css',
})
export class OrganizationsComponent implements OnInit {
    organizations: Organization[] = [];
    total = 0;
    isLoading = true;

    // Add dialog
    showAddDialog = false;
    newOrgName = '';
    isCreating = false;

    // Enrichment
    enrichingOrgId: string | null = null;
    enrichmentMessage = '';

    constructor(private orgService: OrganizationService) { }

    ngOnInit(): void {
        this.loadOrganizations();
    }

    loadOrganizations(): void {
        this.isLoading = true;
        this.orgService.list().subscribe({
            next: (res) => {
                this.organizations = res.items;
                this.total = res.total;
                this.isLoading = false;
            },
            error: () => {
                this.isLoading = false;
            },
        });
    }

    openAddDialog(): void {
        this.showAddDialog = true;
        this.newOrgName = '';
        this.enrichmentMessage = '';
    }

    closeAddDialog(): void {
        this.showAddDialog = false;
    }

    createAndEnrich(): void {
        if (!this.newOrgName.trim()) return;
        this.isCreating = true;
        this.enrichmentMessage = '';

        this.orgService.create({ name: this.newOrgName.trim() }).subscribe({
            next: (org) => {
                this.enrichmentMessage = `✅ ${org.name} created. Enriching with AI...`;
                this.enrichingOrgId = org.id;
                this.loadOrganizations();

                // Auto-enrich
                this.orgService.enrich(org.id).subscribe({
                    next: (result: EnrichmentResult) => {
                        this.enrichingOrgId = null;
                        if (result.status === 'done') {
                            this.enrichmentMessage = `🎉 ${org.name} enriched! ${result.fields_updated} fields filled by AI.`;
                        } else {
                            this.enrichmentMessage = `⚠️ Enrichment partial: ${result.error || 'unknown'}`;
                        }
                        this.loadOrganizations();
                    },
                    error: () => {
                        this.enrichingOrgId = null;
                        this.enrichmentMessage = `⚠️ Enrichment failed. You can retry later.`;
                        this.loadOrganizations();
                    },
                });
            },
            error: () => {
                this.isCreating = false;
                this.enrichmentMessage = '❌ Failed to create organization.';
            },
        });
    }

    getInitials(name: string): string {
        return name
            .split(' ')
            .map((w) => w[0])
            .join('')
            .substring(0, 2)
            .toUpperCase();
    }

    formatRevenue(revenue: number | null): string {
        if (!revenue) return '—';
        if (revenue >= 1_000_000_000) return `$${(revenue / 1_000_000_000).toFixed(1)}B`;
        if (revenue >= 1_000_000) return `$${(revenue / 1_000_000).toFixed(1)}M`;
        if (revenue >= 1_000) return `$${(revenue / 1_000).toFixed(0)}K`;
        return `$${revenue}`;
    }

    getStatusClass(status: string): string {
        switch (status) {
            case 'CUSTOMER': return 'status-badge--accent';
            case 'PROSPECT': return 'status-badge--muted';
            case 'LEAD': return 'status-badge--warn';
            case 'CHURNED': return 'status-badge--danger';
            default: return 'status-badge--muted';
        }
    }

    getLocationString(org: Organization): string {
        const parts = [org.address_city, org.address_country].filter(Boolean);
        return parts.length ? parts.join(', ') : '';
    }
}
