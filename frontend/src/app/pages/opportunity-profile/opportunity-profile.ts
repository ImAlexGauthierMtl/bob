import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DatePipe, UpperCasePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OpportunityService } from '../../shared/services/opportunity.service';
import { ProductService } from '../../shared/services/product.service';
import { ActivityService } from '../../shared/services/activity.service';
import { Opportunity, OpportunityProduct } from '../../shared/models/opportunity.model';
import { Product } from '../../shared/models/product.model';
import { Activity, CreateActivityDto } from '../../shared/models/activity.model';

/** All pipeline stages in display order. */
const STAGES = ['PROSPECTING', 'QUALIFICATION', 'PROPOSAL', 'NEGOTIATION', 'CLOSED_WON', 'CLOSED_LOST'] as const;

/** Human-readable stage labels. */
const STAGE_LABELS: Record<string, string> = {
    PROSPECTING: 'Prospecting',
    QUALIFICATION: 'Qualification',
    PROPOSAL: 'Proposal',
    NEGOTIATION: 'Negotiation',
    CLOSED_WON: 'Closed Won',
    CLOSED_LOST: 'Closed Lost',
};

@Component({
    selector: 'croo-opportunity-profile',
    standalone: true,
    imports: [RouterLink, UpperCasePipe, DatePipe, FormsModule],
    templateUrl: './opportunity-profile.html',
    styleUrl: './opportunity-profile.css',
})
export class OpportunityProfileComponent implements OnInit {
    opp: Opportunity | null = null;
    isLoading = true;
    activeTab = 'overview';

    /** Ordered stage list for the stepper. */
    stages = STAGES.filter(s => s !== 'CLOSED_LOST');

    // ── Product linking ────────────────────────────────
    linkedProducts: OpportunityProduct[] = [];
    productsLoaded = false;

    // Dialog state
    showProductDialog = false;
    availableProducts: Product[] = [];
    productSearch = '';
    addQuantity = 1;
    selectedProductId = '';
    isAddingProduct = false;

    // ── Activities ────────────────────────────────
    activities: Activity[] = [];
    activitiesLoaded = false;

    // Add Activity dialog
    showAddActivityDialog = false;
    newActivitySubject = '';
    newActivityDescription = '';
    newActivityType = 'TASK';
    newActivityPriority = 'MEDIUM';
    newActivityDueDate = '';
    isCreatingActivity = false;

    private route = inject(ActivatedRoute);
    private oppService = inject(OpportunityService);
    private productService = inject(ProductService);
    private actService = inject(ActivityService);

    ngOnInit(): void {
        const id = this.route.snapshot.paramMap.get('id');
        if (id) {
            this.loadOpportunity(id);
        }
    }

    loadOpportunity(id: string): void {
        this.isLoading = true;
        this.oppService.getById(id).subscribe({
            next: (opp) => {
                this.opp = opp;
                this.isLoading = false;
            },
            error: () => {
                this.isLoading = false;
            },
        });
    }

    setActiveTab(tab: string): void {
        this.activeTab = tab;
        if (tab === 'products' && !this.productsLoaded && this.opp) {
            this.loadProducts();
        }
        if (tab === 'activities' && !this.activitiesLoaded && this.opp) {
            this.loadActivities();
        }
    }

    // ── Product management ──────────────────────────────

    loadProducts(): void {
        if (!this.opp) return;
        this.oppService.getProducts(this.opp.id).subscribe({
            next: (res) => {
                this.linkedProducts = res.items;
                this.productsLoaded = true;
            },
        });
    }

    loadActivities(): void {
        if (!this.opp) return;
        this.actService.getAll(0, 50, undefined, undefined, this.opp.id).subscribe({
            next: (res) => {
                this.activities = res.items;
                this.activitiesLoaded = true;
            },
        });
    }

    openProductDialog(): void {
        this.productSearch = '';
        this.addQuantity = 1;
        this.selectedProductId = '';
        this.showProductDialog = true;
        this.searchProducts();
    }

    closeProductDialog(): void {
        this.showProductDialog = false;
    }

    searchProducts(): void {
        this.productService.getAll(0, 20, undefined, undefined).subscribe({
            next: (res) => {
                // Filter out already-linked products
                const linkedIds = new Set(this.linkedProducts.map(lp => lp.product_id));
                this.availableProducts = res.items.filter(p => !linkedIds.has(p.id) && p.is_active);
            },
        });
    }

    get filteredProducts(): Product[] {
        if (!this.productSearch.trim()) return this.availableProducts;
        const q = this.productSearch.toLowerCase();
        return this.availableProducts.filter(p =>
            p.name.toLowerCase().includes(q) ||
            (p.sku && p.sku.toLowerCase().includes(q))
        );
    }

    selectProduct(productId: string): void {
        this.selectedProductId = productId;
    }

    addProduct(): void {
        if (!this.opp || !this.selectedProductId) return;
        this.isAddingProduct = true;
        this.oppService.addProduct(this.opp.id, {
            product_id: this.selectedProductId,
            quantity: this.addQuantity,
        }).subscribe({
            next: () => {
                this.isAddingProduct = false;
                this.showProductDialog = false;
                this.loadProducts();
            },
            error: () => {
                this.isAddingProduct = false;
            },
        });
    }

    removeProduct(line: OpportunityProduct): void {
        if (!this.opp) return;
        this.oppService.removeProduct(this.opp.id, line.id).subscribe({
            next: () => this.loadProducts(),
        });
    }

    getLineTotal(line: OpportunityProduct): number {
        const base = line.unit_price * line.quantity;
        if (line.discount_percent) {
            return base * (1 - line.discount_percent / 100);
        }
        return base;
    }

    getProductsTotal(): number {
        return this.linkedProducts.reduce((sum, l) => sum + this.getLineTotal(l), 0);
    }

    // ── Formatting helpers ──────────────────────────────

    formatAmount(amount: number | null): string {
        if (!amount) return '—';
        if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
        if (amount >= 1_000) return `$${(amount / 1_000).toFixed(0)}K`;
        return `$${amount.toLocaleString()}`;
    }

    formatAmountFull(amount: number | null): string {
        if (!amount) return '—';
        return `$${amount.toLocaleString()}`;
    }

    formatPrice(price: number): string {
        return `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    getStageLabel(stage: string): string {
        return STAGE_LABELS[stage] || stage;
    }

    getStageBadgeClass(stage: string): string {
        const map: Record<string, string> = {
            PROSPECTING: 'stage-badge--blue',
            QUALIFICATION: 'stage-badge--yellow',
            PROPOSAL: 'stage-badge--purple',
            NEGOTIATION: 'stage-badge--green',
            CLOSED_WON: 'stage-badge--green',
            CLOSED_LOST: 'stage-badge--red',
        };
        return map[stage] || '';
    }

    /** Returns which stepper index the current stage corresponds to (0-based). */
    getStageIndex(): number {
        if (!this.opp) return 0;
        const idx = this.stages.indexOf(this.opp.stage as any);
        return idx >= 0 ? idx : 0;
    }

    /** Returns stepper progress bar width as a percentage string. */
    getStepperProgress(): string {
        const idx = this.getStageIndex();
        const max = this.stages.length - 1;
        return `${(idx / max) * 100}%`;
    }

    /** Determines step class for stage stepper. */
    getStepClass(stageIndex: number): string {
        const current = this.getStageIndex();
        if (stageIndex < current) return 'stepper-step--done';
        if (stageIndex === current) return 'stepper-step--active';
        return 'stepper-step--pending';
    }

    getPriorityClass(priority: string): string {
        const map: Record<string, string> = {
            LOW: 'priority-badge--blue',
            MEDIUM: 'priority-badge--yellow',
            HIGH: 'priority-badge--red',
            CRITICAL: 'priority-badge--red',
        };
        return map[priority] || '';
    }

    getCategoryIcon(category: string): string {
        switch (category) {
            case 'SOFTWARE': return 'fa-solid fa-laptop-code';
            case 'SERVICE': return 'fa-solid fa-cloud';
            case 'ADD_ON': return 'fa-solid fa-puzzle-piece';
            case 'CONSULTING': return 'fa-solid fa-briefcase';
            case 'HARDWARE': return 'fa-solid fa-microchip';
            default: return 'fa-solid fa-box';
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
        if (!this.newActivitySubject.trim() || !this.opp) return;
        this.isCreatingActivity = true;

        const data: CreateActivityDto = {
            subject: this.newActivitySubject,
            description: this.newActivityDescription || undefined,
            activity_type: this.newActivityType,
            priority: this.newActivityPriority,
            opportunity_ids: [this.opp.id],
        };
        if (this.opp.organization_id) {
            data.organization_ids = [this.opp.organization_id];
        }
        if (this.newActivityDueDate) {
            data.due_date = this.newActivityDueDate;
        }

        this.actService.create(data).subscribe({
            next: () => {
                this.showAddActivityDialog = false;
                this.isCreatingActivity = false;
                this.loadActivities();
            },
            error: () => {
                this.isCreatingActivity = false;
            },
        });
    }
}
