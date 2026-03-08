import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { QuoteService } from '../../shared/services/quote.service';
import { Quote } from '../../shared/models/quote.model';

@Component({
    selector: 'croo-quotes',
    standalone: true,
    imports: [RouterLink],
    templateUrl: './quotes.html',
    styleUrl: './quotes.css',
})
export class QuotesComponent implements OnInit {
    quotes: Quote[] = [];
    total = 0;
    isLoading = true;

    private quoteService = inject(QuoteService);

    ngOnInit(): void {
        this.loadQuotes();
    }

    loadQuotes(): void {
        this.isLoading = true;
        this.quoteService.getAll().subscribe({
            next: (res) => {
                this.quotes = res.items;
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

    getStatusClass(status: string): string {
        switch (status) {
            case 'ACCEPTED': return 'status-badge--accent';
            case 'REJECTED': return 'status-badge--danger';
            case 'SENT': return 'status-badge--warn';
            case 'EXPIRED': return 'status-badge--muted';
            default: return 'status-badge--muted';
        }
    }
}
