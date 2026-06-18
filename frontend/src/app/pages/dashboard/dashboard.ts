import { AsyncPipe, DecimalPipe } from '@angular/common';
import { AfterViewInit, Component, OnInit, inject } from '@angular/core';
import { Store } from '@ngrx/store';
import { combineLatest, map } from 'rxjs';
import { CrmDashboardSummary } from '../../shared/services/crm-b4f.service';
import type { AppState } from '../../store';
import { loadCrmDashboard } from '../../store/crm/crm.actions';
import { selectCrmDashboard, selectCrmError, selectCrmLoading } from '../../store/crm/crm.selectors';

interface DashboardMetric {
    label: string;
    value: number;
    context: string;
}

interface DashboardProgress {
    label: string;
    value: number;
    width: number;
}

interface DashboardHighlight {
    name: string;
    detail: string;
    initials: string;
}

interface DashboardAction {
    label: string;
    count: number;
}

@Component({
    selector: 'croo-dashboard',
    standalone: true,
    imports: [AsyncPipe, DecimalPipe],
    templateUrl: './dashboard.html',
    styleUrl: './dashboard.css',
})
export class DashboardComponent implements OnInit, AfterViewInit {
    private store: Store<AppState> = inject(Store);
    private dashboard$ = this.store.select(selectCrmDashboard);

    readonly vm$ = combineLatest({
        data: this.dashboard$,
        loading: this.store.select(selectCrmLoading),
        error: this.store.select(selectCrmError),
        metrics: this.dashboard$.pipe(map((data) => this.buildMetrics(data))),
        pipeline: this.dashboard$.pipe(map((data) => this.buildPipeline(data))),
        pipelineTotal: this.dashboard$.pipe(
            map((data) => this.total(data, 'open_opportunities') + this.total(data, 'pending_activities') + this.total(data, 'products')),
        ),
        productsTotal: this.dashboard$.pipe(map((data) => this.total(data, 'products'))),
        topRecords: this.dashboard$.pipe(map((data) => this.buildTopRecords(data))),
        actions: this.dashboard$.pipe(map((data) => this.buildActions(data))),
    });

    ngOnInit(): void {
        this.store.dispatch(loadCrmDashboard());
    }

    ngAfterViewInit(): void {
        setTimeout(() => this.renderCharts(), 100);
    }

    private buildMetrics(data: CrmDashboardSummary | null): DashboardMetric[] {
        return [
            { label: 'Organizations', value: this.total(data, 'organizations'), context: 'CRM accounts' },
            { label: 'Contacts', value: this.total(data, 'contacts'), context: 'People tracked' },
            { label: 'Open Opportunities', value: this.total(data, 'open_opportunities'), context: 'Pipeline items' },
            { label: 'Pending Activities', value: this.total(data, 'pending_activities'), context: 'Follow-ups' },
        ];
    }

    private buildPipeline(data: CrmDashboardSummary | null): DashboardProgress[] {
        const items = [
            { label: 'Open opportunities', value: this.total(data, 'open_opportunities') },
            { label: 'Pending activities', value: this.total(data, 'pending_activities') },
            { label: 'Products', value: this.total(data, 'products') },
        ];
        const max = Math.max(...items.map((item) => item.value), 1);
        return items.map((item) => ({
            ...item,
            width: item.value > 0 ? Math.max(Math.round((item.value / max) * 100), 6) : 0,
        }));
    }

    private buildTopRecords(data: CrmDashboardSummary | null): DashboardHighlight[] {
        const organizations = this.highlights(data, 'organizations');
        const contacts = this.highlights(data, 'contacts');
        return [...organizations, ...contacts].slice(0, 5);
    }

    private buildActions(data: CrmDashboardSummary | null): DashboardAction[] {
        return (data?.next_actions ?? []).map((action) => ({
            label: action.label,
            count: action.count,
        }));
    }

    private total(data: CrmDashboardSummary | null, key: string): number {
        return data?.totals[key] ?? 0;
    }

    private highlights(data: CrmDashboardSummary | null, key: string): DashboardHighlight[] {
        const items = data?.highlights[key] ?? [];
        return items.map((item) => this.toHighlight(item)).slice(0, 5);
    }

    private toHighlight(item: unknown): DashboardHighlight {
        const record = this.toRecord(item);
        const name = this.text(record, ['name', 'display_name', 'full_name', 'email'], 'CRM record');
        const firstName = this.text(record, ['first_name'], '');
        const lastName = this.text(record, ['last_name'], '');
        const contactName = `${firstName} ${lastName}`.trim();
        const resolvedName = contactName || name;
        return {
            name: resolvedName,
            detail: this.text(record, ['status', 'stage', 'kind', 'email'], 'Tracked record'),
            initials: this.initials(resolvedName),
        };
    }

    private toRecord(item: unknown): Record<string, unknown> {
        return item && typeof item === 'object' ? item as Record<string, unknown> : {};
    }

    private text(record: Record<string, unknown>, keys: string[], fallback: string): string {
        for (const key of keys) {
            const value = record[key];
            if (typeof value === 'string' && value.trim()) {
                return value;
            }
        }
        return fallback;
    }

    private initials(name: string): string {
        const parts = name.split(/\s+/).filter(Boolean).slice(0, 2);
        const letters = parts.map((part) => part[0]?.toUpperCase() ?? '').join('');
        return letters || 'CR';
    }

    renderCharts(): void {
        try {
            const Plotly = (window as any).Plotly;
            if (!Plotly) return;

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
