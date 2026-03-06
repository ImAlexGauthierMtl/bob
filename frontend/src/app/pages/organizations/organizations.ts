import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import {
    OrganizationService,
    Organization,
    PlaceResult,
    EnrichmentResult,
    CreateOrganizationRequest,
} from '../../shared/services/organization.service';

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

    // Dialog state
    showAddDialog = false;
    searchQuery = '';
    isSearching = false;
    searchResults: PlaceResult[] = [];
    hasSearched = false;

    // Manual entry (when no results)
    showManualForm = false;
    manualName = '';
    manualIndustry = '';
    manualPhone = '';
    manualWebsite = '';
    manualAddress = '';

    // Creation + enrichment
    isCreating = false;
    enrichingOrgId: string | null = null;
    statusMessage = '';
    statusType: 'info' | 'success' | 'error' = 'info';

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

    // ── Dialog ──────────────────────────────

    openAddDialog(): void {
        this.showAddDialog = true;
        this.resetDialog();
    }

    closeAddDialog(): void {
        this.showAddDialog = false;
    }

    resetDialog(): void {
        this.searchQuery = '';
        this.searchResults = [];
        this.hasSearched = false;
        this.showManualForm = false;
        this.isSearching = false;
        this.isCreating = false;
        this.statusMessage = '';
        this.manualName = '';
        this.manualIndustry = '';
        this.manualPhone = '';
        this.manualWebsite = '';
        this.manualAddress = '';
    }

    // ── Step 1: Search ──────────────────────

    searchMaps(): void {
        if (!this.searchQuery.trim()) return;
        this.isSearching = true;
        this.hasSearched = false;
        this.searchResults = [];
        this.showManualForm = false;
        this.statusMessage = '';

        this.orgService.searchMaps(this.searchQuery.trim()).subscribe({
            next: (res) => {
                this.searchResults = res.results;
                this.hasSearched = true;
                this.isSearching = false;
                if (res.results.length === 0) {
                    this.showManualForm = true;
                    this.manualName = this.searchQuery.trim();
                }
            },
            error: () => {
                this.isSearching = false;
                this.hasSearched = true;
                this.showManualForm = true;
                this.manualName = this.searchQuery.trim();
                this.statusMessage = '⚠️ Search service unavailable. Enter details manually.';
                this.statusType = 'error';
            },
        });
    }

    // ── Step 2: Select result ───────────────

    selectPlace(place: PlaceResult): void {
        this.isCreating = true;
        this.statusMessage = `Creating ${place.title}...`;
        this.statusType = 'info';

        // Parse address from Maps format "269 Rue Racine E, Chicoutimi, QC G7H 1S5, Canada"
        const addressParts = place.address.split(', ');
        const createData: CreateOrganizationRequest = {
            name: place.title,
            industry: place.industry || undefined,
            website: place.website || undefined,
            phone: place.phone || undefined,
            address_street: addressParts[0] || undefined,
            address_city: addressParts[1] || undefined,
            status: 'PROSPECT',
        };

        // Parse state/postal and country from remaining parts
        if (addressParts.length >= 4) {
            // "QC G7H 1S5" → state + postal
            const statePostal = addressParts[2] || '';
            const spaceIdx = statePostal.indexOf(' ');
            if (spaceIdx > 0) {
                createData.address_state = statePostal.substring(0, spaceIdx);
                createData.address_postal_code = statePostal.substring(spaceIdx + 1);
            } else {
                createData.address_state = statePostal;
            }
            createData.address_country = addressParts[3];
        } else if (addressParts.length === 3) {
            createData.address_country = addressParts[2];
        }

        this.createAndEnrich(createData);
    }

    // ── Manual entry ────────────────────────

    submitManual(): void {
        if (!this.manualName.trim()) return;
        this.isCreating = true;
        this.statusMessage = `Creating ${this.manualName}...`;
        this.statusType = 'info';

        this.createAndEnrich({
            name: this.manualName.trim(),
            industry: this.manualIndustry || undefined,
            phone: this.manualPhone || undefined,
            website: this.manualWebsite || undefined,
            status: 'PROSPECT',
        });
    }

    // ── Create + Enrich ─────────────────────

    private createAndEnrich(data: CreateOrganizationRequest): void {
        this.orgService.create(data).subscribe({
            next: (org) => {
                this.statusMessage = `✅ ${org.name} created! AI enrichment starting...`;
                this.statusType = 'success';
                this.enrichingOrgId = org.id;
                this.loadOrganizations();

                // Auto-enrich in background
                this.orgService.enrich(org.id).subscribe({
                    next: (result: EnrichmentResult) => {
                        this.enrichingOrgId = null;
                        if (result.status === 'done') {
                            this.statusMessage = `🎉 ${org.name} enriched! ${result.fields_updated} fields filled by AI.`;
                        } else {
                            this.statusMessage = `⚠️ Partial enrichment: ${result.error || 'unknown'}`;
                            this.statusType = 'error';
                        }
                        this.loadOrganizations();
                    },
                    error: () => {
                        this.enrichingOrgId = null;
                        this.statusMessage = `⚠️ Enrichment failed. You can retry later.`;
                        this.statusType = 'error';
                    },
                });
            },
            error: () => {
                this.isCreating = false;
                this.statusMessage = '❌ Failed to create organization.';
                this.statusType = 'error';
            },
        });
    }

    // ── Helpers ──────────────────────────────

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
