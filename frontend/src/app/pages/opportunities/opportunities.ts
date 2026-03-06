import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { OpportunityService, Opportunity } from '../../shared/services/opportunity.service';

@Component({
    selector: 'croo-opportunities',
    standalone: true,
    imports: [RouterLink],
    templateUrl: './opportunities.html',
    styleUrl: './opportunities.css',
})
export class OpportunitiesComponent implements OnInit {
    opportunities: Opportunity[] = [];
    total = 0;
    isLoading = true;

    constructor(private oppService: OpportunityService) { }

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
            },
            error: () => (this.isLoading = false),
        });
    }

    formatAmount(amount: number | null): string {
        if (!amount) return '—';
        return '$' + amount.toLocaleString();
    }

    getStageClass(stage: string): string {
        switch (stage) {
            case 'CLOSED_WON': return 'status-badge--accent';
            case 'CLOSED_LOST': return 'status-badge--danger';
            case 'NEGOTIATION': return 'status-badge--warn';
            default: return 'status-badge--muted';
        }
    }
}
