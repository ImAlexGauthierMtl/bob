import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { OrganizationService } from '../../shared/services/organization.service';
import { BobActionService } from '../../shared/services/bob-action.service';
import { Organization, PlaceResult, CreateOrganizationDto } from '../../shared/models/organization.model';

@Component({
    selector: 'croo-organizations',
    standalone: true,
    imports: [RouterLink, FormsModule],
    templateUrl: './organizations.html',
    styleUrl: './organizations.css',
})
export class OrganizationsComponent implements OnInit, OnDestroy {
    organizations: Organization[] = [];
    total = 0;
    isLoading = true;

    // Pagination
    currentPage = 1;
    pageSize = 50;
    totalPages = 1;
    Math = Math;

    // Dialog state
    showAddDialog = false;
    searchQuery = '';
    isSearching = false;
    searchResults: PlaceResult[] = [];
    hasSearched = false;

    // Manual entry
    showManualForm = false;
    manualName = '';
    manualIndustry = '';
    manualPhone = '';
    manualWebsite = '';

    // Creation
    isCreating = false;
    statusMessage = '';
    statusType: 'info' | 'success' | 'error' = 'info';

    private bobActionSub?: Subscription;

    private orgService = inject(OrganizationService);
    private router = inject(Router);
    private bobActionService = inject(BobActionService);

    ngOnInit(): void {
        this.loadOrganizations();

        console.log('[Organizations] subscribing to BobActionService.action$');
        this.bobActionSub = this.bobActionService.action$.subscribe(action => {
            console.log('[Organizations] received action:', JSON.stringify(action));
            if (action.type === 'open_create_dialog' && action.entity === 'organization') {
                console.log('[Organizations] ✅ match! calling openAddDialog()');
                this.openAddDialog(action.name);
            } else if (action.type === 'ui_update_input' && this.showAddDialog) {
                if (action.text !== undefined) {
                    this.searchQuery = action.text;
                }
                if (action.submit) {
                    this.searchMaps();
                }
            } else if (action.type === 'ui_select_result' && this.showAddDialog) {
                if (action.index !== undefined && action.index > 0 && this.searchResults.length >= action.index) {
                    this.selectPlace(this.searchResults[action.index - 1]);
                }
            }
        });
    }

    ngOnDestroy(): void {
        this.bobActionSub?.unsubscribe();
    }

    loadOrganizations(): void {
        this.isLoading = true;
        const skip = (this.currentPage - 1) * this.pageSize;
        this.orgService.getAll(skip, this.pageSize).subscribe({
            next: (res) => {
                this.organizations = res.items;
                this.total = res.total;
                this.totalPages = Math.max(1, Math.ceil(this.total / this.pageSize));
                this.isLoading = false;
            },
            error: () => {
                this.isLoading = false;
            },
        });
    }

    goToPage(page: number): void {
        if (page < 1 || page > this.totalPages) return;
        this.currentPage = page;
        this.loadOrganizations();
    }

    onPageSizeChange(event: Event): void {
        this.pageSize = +(event.target as HTMLSelectElement).value;
        this.currentPage = 1;
        this.loadOrganizations();
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

    openAddDialog(name?: string): void {
        this.showAddDialog = true;
        this.resetDialog();
        // If a name was provided (from Bob), pre-fill and auto-search
        if (name) {
            this.searchQuery = name;
            // Let Angular detect the change before searching
            setTimeout(() => this.searchMaps(), 100);
        }
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
    }

    // ── Step 1: Search Maps ─────────────────

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
                this.statusMessage = '⚠️ Search unavailable. Enter details manually.';
                this.statusType = 'error';
            },
        });
    }

    // ── Step 2: Select → Create → Redirect ──

    selectPlace(place: PlaceResult): void {
        this.isCreating = true;

        const addressParts = place.address.split(', ');
        const createData: CreateOrganizationDto = {
            name: place.title,
            industry: place.industry || undefined,
            website: place.website || undefined,
            phone: place.phone || undefined,
            address_street: addressParts[0] || undefined,
            address_city: addressParts[1] || undefined,
            status: 'PROSPECT',
        };

        if (addressParts.length >= 4) {
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

        this.createAndRedirect(createData);
    }

    submitManual(): void {
        if (!this.manualName.trim()) return;
        this.isCreating = true;

        this.createAndRedirect({
            name: this.manualName.trim(),
            industry: this.manualIndustry || undefined,
            phone: this.manualPhone || undefined,
            website: this.manualWebsite || undefined,
            status: 'PROSPECT',
        });
    }

    // ── Create → fire enrich in background → redirect ──

    private createAndRedirect(data: CreateOrganizationDto): void {
        this.orgService.create(data).subscribe({
            next: (org) => {
                // Fire enrichment in background (non-blocking, returns immediately)
                this.orgService.enrich(org.id).subscribe();

                // Close dialog and redirect to org page immediately
                this.showAddDialog = false;
                this.router.navigate(['/organizations', org.id]);
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
