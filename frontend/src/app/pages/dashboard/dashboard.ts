import { Component, OnInit, AfterViewInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { OrganizationService } from '../../shared/services/organization.service';
import { ContactService } from '../../shared/services/contact.service';
import { OpportunityService } from '../../shared/services/opportunity.service';
import { QuoteService } from '../../shared/services/quote.service';
import { ActivityService } from '../../shared/services/activity.service';

@Component({
    selector: 'croo-dashboard',
    standalone: true,
    imports: [RouterLink],
    templateUrl: './dashboard.html',
    styleUrl: './dashboard.css',
})
export class DashboardComponent implements OnInit, AfterViewInit {
    orgCount = 0;
    contactCount = 0;
    oppCount = 0;
    quoteCount = 0;
    activityCount = 0;
    isLoading = true;

    private orgService = inject(OrganizationService);
    private contactService = inject(ContactService);
    private oppService = inject(OpportunityService);
    private quoteService = inject(QuoteService);
    private actService = inject(ActivityService);

    ngOnInit(): void {
        this.loadCounts();
    }

    ngAfterViewInit(): void {
        setTimeout(() => this.renderCharts(), 100);
    }

    loadCounts(): void {
        this.isLoading = true;
        let loaded = 0;
        const checkDone = () => { loaded++; if (loaded >= 5) this.isLoading = false; };

        this.orgService.getAll(0, 1).subscribe({ next: (r) => { this.orgCount = r.total; checkDone(); }, error: checkDone });
        this.contactService.getAll(0, 1).subscribe({ next: (r) => { this.contactCount = r.total; checkDone(); }, error: checkDone });
        this.oppService.getAll(0, 1).subscribe({ next: (r) => { this.oppCount = r.total; checkDone(); }, error: checkDone });
        this.quoteService.getAll(0, 1).subscribe({ next: (r) => { this.quoteCount = r.total; checkDone(); }, error: checkDone });
        this.actService.getAll(0, 1).subscribe({ next: (r) => { this.activityCount = r.total; checkDone(); }, error: checkDone });
    }

    renderCharts(): void {
        try {
            const Plotly = (window as any).Plotly;
            if (!Plotly) return;

            // Revenue Chart
            const revenueData = [{
                type: 'scatter',
                mode: 'lines',
                x: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                y: [185000, 192000, 201000, 198000, 215000, 228000, 234000, 242000, 238000, 251000, 263000, 278000],
                line: { color: '#FF4500', width: 2 },
                hovertemplate: '<b>%{x}</b><br>$%{y:,.0f}<extra></extra>'
            }];

            const revenueLayout = {
                margin: { t: 20, r: 20, b: 40, l: 60 },
                plot_bgcolor: 'transparent',
                paper_bgcolor: 'transparent',
                xaxis: { showgrid: false, zeroline: false, showline: true, linecolor: '#E5E7EB', linewidth: 1 },
                yaxis: { showgrid: true, gridcolor: '#F3F4F6', zeroline: false, showline: false, tickformat: '$,.0f' },
                hovermode: 'x unified',
                showlegend: false
            };

            Plotly.newPlot('revenue-chart', revenueData, revenueLayout, { responsive: true, displayModeBar: false });

            // Team Performance Chart
            const teamData = [{
                type: 'bar',
                x: ['Sarah Johnson', 'Michael Chen', 'Emily Rodriguez', 'David Kim', 'Jessica Williams'],
                y: [487000, 452000, 418000, 395000, 367000],
                marker: { color: '#FF4500' },
                hovertemplate: '<b>%{x}</b><br>$%{y:,.0f}<extra></extra>'
            }];

            const teamLayout = {
                margin: { t: 20, r: 20, b: 80, l: 60 },
                plot_bgcolor: 'transparent',
                paper_bgcolor: 'transparent',
                xaxis: { showgrid: false, zeroline: false, showline: true, linecolor: '#E5E7EB', linewidth: 1 },
                yaxis: { showgrid: true, gridcolor: '#F3F4F6', zeroline: false, showline: false, tickformat: '$,.0f' },
                showlegend: false
            };

            Plotly.newPlot('team-performance-chart', teamData, teamLayout, { responsive: true, displayModeBar: false });

        } catch (e) {
            console.error('Error rendering dashboard charts:', e);
        }
    }
}
