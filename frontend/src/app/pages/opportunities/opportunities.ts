import { Component, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DecimalPipe, SlicePipe } from '@angular/common';
import { OpportunityService, Opportunity, CreateOpportunityRequest } from '../../shared/services/opportunity.service';
import { OrganizationService } from '../../shared/services/organization.service';

@Component({
    selector: 'croo-opportunities',
    standalone: true,
    imports: [RouterLink, FormsModule, DecimalPipe, SlicePipe],
    templateUrl: './opportunities.html',
    styleUrl: './opportunities.css',
})
export class OpportunitiesComponent implements OnInit {
    opportunities: Opportunity[] = [];
    total = 0;
    isLoading = true;

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
    parsedPreview: Partial<CreateOpportunityRequest> | null = null;

    constructor(
        private oppService: OpportunityService,
        private orgService: OrganizationService,
        private router: Router,
    ) { }

    ngOnInit(): void {
        this.loadOpportunities();
    }

    loadOpportunities(): void {
        this.isLoading = true;
        this.oppService.list().subscribe({
            next: (res) => {
                this.opportunities = res.items;
                this.total = res.total;
                this.isLoading = false;
                this.resolveOrgNames();
                this.pipelineValue = this.opportunities.reduce((sum, o) => sum + (o.amount || 0), 0);
            },
            error: () => (this.isLoading = false),
        });
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

        const data: CreateOpportunityRequest = {
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

    private parseOppText(text: string): Partial<CreateOpportunityRequest> {
        const result: Partial<CreateOpportunityRequest> = {};

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
