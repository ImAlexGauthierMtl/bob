import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DecimalPipe, SlicePipe } from '@angular/common';
import { Subscription } from 'rxjs';
import { OpportunityService } from '../../shared/services/opportunity.service';
import { OrganizationService } from '../../shared/services/organization.service';
import { BobActionService } from '../../shared/services/bob-action.service';
import { Opportunity, CreateOpportunityDto } from '../../shared/models/opportunity.model';

@Component({
    selector: 'croo-opportunities',
    standalone: true,
    imports: [RouterLink, FormsModule, DecimalPipe, SlicePipe],
    templateUrl: './opportunities.html',
    styleUrl: './opportunities.css',
})
export class OpportunitiesComponent implements OnInit, OnDestroy {
    opportunities: Opportunity[] = [];
    total = 0;
    isLoading = true;

    // Pagination
    currentPage = 1;
    pageSize = 50;
    totalPages = 1;
    Math = Math;

    // Org name resolution
    orgNames: Record<string, string> = {};

    // Pipeline stats
    pipelineValue = 0;

    // Dialog state
    showAddDialog = false;
    oppInput = '';
    isProcessing = false;
    isCreating = false;
    statusMessage = '';
    parsedPreview: Partial<CreateOpportunityDto> | null = null;

    private bobActionSub?: Subscription;

    private oppService = inject(OpportunityService);
    private orgService = inject(OrganizationService);
    private router = inject(Router);
    private bobActionService = inject(BobActionService);

    ngOnInit(): void {
        this.loadOpportunities();

        this.bobActionSub = this.bobActionService.action$.subscribe(action => {
            if (action.type === 'open_create_dialog' && action.entity === 'opportunity') {
                this.openAddDialog();
            }
        });
    }

    ngOnDestroy(): void {
        this.bobActionSub?.unsubscribe();
    }

    loadOpportunities(): void {
        this.isLoading = true;
        const skip = (this.currentPage - 1) * this.pageSize;
        this.oppService.getAll(skip, this.pageSize).subscribe({
            next: (res) => {
                this.opportunities = res.items;
                this.total = res.total;
                this.totalPages = Math.max(1, Math.ceil(this.total / this.pageSize));
                this.isLoading = false;
                this.resolveOrgNames();
                this.pipelineValue = this.opportunities.reduce((sum, o) => sum + (o.amount || 0), 0);
            },
            error: () => (this.isLoading = false),
        });
    }

    goToPage(page: number): void {
        if (page < 1 || page > this.totalPages) return;
        this.currentPage = page;
        this.loadOpportunities();
    }

    onPageSizeChange(event: Event): void {
        this.pageSize = +(event.target as HTMLSelectElement).value;
        this.currentPage = 1;
        this.loadOpportunities();
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

    formatAmount(amount: number | null): string {
        if (!amount) return '—';
        return '$' + amount.toLocaleString();
    }

    formatPipelineValue(): string {
        if (this.pipelineValue >= 1_000_000) return '$' + (this.pipelineValue / 1_000_000).toFixed(1) + 'M';
        if (this.pipelineValue >= 1_000) return '$' + (this.pipelineValue / 1_000).toFixed(0) + 'K';
        return '$' + this.pipelineValue;
    }

    getStageClass(stage: string): string {
        switch (stage) {
            case 'CLOSED_WON': return 'stage-badge--green';
            case 'CLOSED_LOST': return 'stage-badge--red';
            case 'NEGOTIATION': return 'stage-badge--purple';
            case 'PROPOSAL': return 'stage-badge--blue';
            case 'QUALIFICATION': return 'stage-badge--yellow';
            case 'PROSPECTING': return 'stage-badge--yellow';
            default: return 'stage-badge--yellow';
        }
    }

    getStageDotClass(stage: string): string {
        switch (stage) {
            case 'CLOSED_WON': return 'dot--green';
            case 'CLOSED_LOST': return 'dot--red';
            case 'NEGOTIATION': return 'dot--purple';
            case 'PROPOSAL': return 'dot--blue';
            default: return 'dot--yellow';
        }
    }

    getInitials(name: string): string {
        return name.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase();
    }

    private resolveOrgNames(): void {
        const orgIds = [...new Set(
            this.opportunities.map(o => o.organization_id).filter((id): id is string => !!id)
        )];
        for (const id of orgIds) {
            this.orgService.getById(id).subscribe({
                next: (org) => this.orgNames[id] = org.name,
            });
        }
    }

    // ── Dialog ──────────────────────────────

    openAddDialog(): void {
        this.showAddDialog = true;
        this.oppInput = '';
        this.isProcessing = false;
        this.isCreating = false;
        this.statusMessage = '';
        this.parsedPreview = null;
    }

    closeAddDialog(): void {
        this.showAddDialog = false;
    }

    processInput(): void {
        if (!this.oppInput.trim()) return;
        this.isProcessing = true;
        this.statusMessage = '';
        this.parsedPreview = null;

        setTimeout(() => {
            this.parsedPreview = this.parseOppText(this.oppInput);
            this.isProcessing = false;
        }, 600);
    }

    createFromParsed(): void {
        if (!this.parsedPreview?.name) return;
        this.isCreating = true;

        const data: CreateOpportunityDto = {
            name: this.parsedPreview.name,
            description: this.parsedPreview.description,
            stage: this.parsedPreview.stage || 'PROSPECTING',
            priority: this.parsedPreview.priority || 'MEDIUM',
            amount: this.parsedPreview.amount,
            probability: this.parsedPreview.probability,
            organization_id: this.parsedPreview.organization_id,
        };

        this.oppService.create(data).subscribe({
            next: (opp) => {
                this.showAddDialog = false;
                this.loadOpportunities();
            },
            error: () => {
                this.isCreating = false;
                this.statusMessage = '❌ Failed to create opportunity.';
            },
        });
    }

    private parseOppText(text: string): Partial<CreateOpportunityDto> {
        const result: Partial<CreateOpportunityDto> = {};

        const amountMatch = text.match(/\$([\d,]+(?:\.\d{1,2})?)\s*([KkMm])?/);
        if (amountMatch) {
            let amount = parseFloat(amountMatch[1].replace(/,/g, ''));
            const suffix = amountMatch[2]?.toUpperCase();
            if (suffix === 'K') amount *= 1_000;
            if (suffix === 'M') amount *= 1_000_000;
            result.amount = amount;
            text = text.replace(amountMatch[0], '');
        }

        const probMatch = text.match(/(\d{1,3})\s*%/);
        if (probMatch) {
            result.probability = parseInt(probMatch[1], 10);
            text = text.replace(probMatch[0], '');
        }

        const stageMap: Record<string, string> = {
            'prospecting': 'PROSPECTING', 'prospect': 'PROSPECTING',
            'qualification': 'QUALIFICATION', 'qualified': 'QUALIFICATION',
            'proposal': 'PROPOSAL', 'negotiation': 'NEGOTIATION',
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

        text = text.replace(/[,;|·•—–]+/g, ' ').replace(/\s+/g, ' ').trim();
        result.name = text || 'New Opportunity';

        return result;
    }
}
