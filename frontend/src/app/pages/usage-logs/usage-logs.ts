import { Component, OnInit, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { environment } from '../../../environments/environment';

interface UsageLog {
    id: string;
    timestamp: string;
    service_type: string;
    provider: string;
    model: string;
    trigger_source: string;
    trigger_id: string;
    correlation_id: string;
    correlation_label: string;
    input_tokens: number;
    output_tokens: number;
    audio_seconds: number;
    characters: number;
    cogs_amount: number;
    cogs_currency: string;
    tenant_id: string;
    user_id: string;
    user_email: string;
    is_billable: boolean;
    metadata_: Record<string, unknown> | null;
}

interface UsageListResponse {
    items: UsageLog[];
    total: number;
    skip: number;
    limit: number;
}

interface IntentGroup {
    correlation_id: string;
    correlation_label: string;
    transaction_count: number;
    total_cogs: number;
    first_timestamp: string;
    service_types: string[];
    trigger_source: string;
    tenant_id: string;
    user_email: string;
}

interface IntentListResponse {
    items: IntentGroup[];
    total: number;
    skip: number;
    limit: number;
    total_cogs: number;
}

type ViewMode = 'transactions' | 'intents';

@Component({
    selector: 'croo-usage-logs',
    standalone: true,
    imports: [FormsModule],
    templateUrl: './usage-logs.html',
    styleUrl: './usage-logs.css',
})
export class UsageLogsComponent implements OnInit {
    // ── View mode ──
    viewMode: ViewMode = 'transactions';

    // ── Transaction view ──
    logItems: UsageLog[] = [];
    logTotal = 0;
    logTotalCogs = 0;
    logOffset = 0;
    logLimit = 50;
    filterService = '';
    filterTenant = '';
    isLoading = false;

    // ── Intent view ──
    intentItems: IntentGroup[] = [];
    intentTotal = 0;
    intentTotalCogs = 0;
    intentOffset = 0;
    intentLimit = 50;

    // ── Detail drawer ──
    drawerOpen = false;
    drawerIntent: IntentGroup | null = null;
    drawerItems: UsageLog[] = [];
    drawerLoading = false;

    Math = Math;
    JSON = JSON;

    private http = inject(HttpClient);

    ngOnInit(): void {
        this.loadLogs();
    }

    switchView(mode: ViewMode): void {
        this.viewMode = mode;
        if (mode === 'intents' && this.intentItems.length === 0) {
            this.loadIntents();
        }
    }

    loadLogs(): void {
        this.isLoading = true;
        let url = `${environment.platformApiUrl}/admin/usage?skip=${this.logOffset}&limit=${this.logLimit}`;
        if (this.filterService) url += `&service_type=${this.filterService}`;
        if (this.filterTenant) url += `&tenant_id=${this.filterTenant}`;

        this.http.get<UsageListResponse>(url).subscribe({
            next: (res) => {
                this.logItems = res.items;
                this.logTotal = res.total;
                this.logTotalCogs = res.items.reduce((sum, i) => sum + (i.cogs_amount || 0), 0);
                this.isLoading = false;
            },
            error: () => {
                this.isLoading = false;
                this.logItems = [];
                this.logTotal = 0;
            },
        });
    }

    loadIntents(): void {
        this.isLoading = true;
        let url = `${environment.platformApiUrl}/admin/usage/by-intent?skip=${this.intentOffset}&limit=${this.intentLimit}`;
        if (this.filterTenant) url += `&tenant_id=${this.filterTenant}`;

        this.http.get<IntentListResponse>(url).subscribe({
            next: (res) => {
                this.intentItems = res.items;
                this.intentTotal = res.total;
                this.intentTotalCogs = res.total_cogs;
                this.isLoading = false;
            },
            error: () => {
                this.isLoading = false;
                this.intentItems = [];
                this.intentTotal = 0;
            },
        });
    }

    openIntentDetail(intent: IntentGroup): void {
        this.drawerOpen = true;
        this.drawerIntent = intent;
        this.drawerLoading = true;
        this.drawerItems = [];

        this.http.get<UsageListResponse>(
            `${environment.platformApiUrl}/admin/usage/by-intent/${intent.correlation_id}`
        ).subscribe({
            next: (res) => {
                this.drawerItems = res.items;
                this.drawerLoading = false;
            },
            error: () => {
                this.drawerLoading = false;
                this.drawerItems = [];
            },
        });
    }

    closeDrawer(): void {
        this.drawerOpen = false;
        this.drawerIntent = null;
        this.drawerItems = [];
    }

    resetFilters(): void {
        this.filterService = '';
        this.filterTenant = '';
        this.logOffset = 0;
        this.intentOffset = 0;
        if (this.viewMode === 'transactions') {
            this.loadLogs();
        } else {
            this.loadIntents();
        }
    }

    onFilterChange(): void {
        this.logOffset = 0;
        this.intentOffset = 0;
        if (this.viewMode === 'transactions') {
            this.loadLogs();
        } else {
            this.loadIntents();
        }
    }

    prevPage(): void {
        if (this.viewMode === 'transactions') {
            this.logOffset = Math.max(0, this.logOffset - this.logLimit);
            this.loadLogs();
        } else {
            this.intentOffset = Math.max(0, this.intentOffset - this.intentLimit);
            this.loadIntents();
        }
    }

    nextPage(): void {
        if (this.viewMode === 'transactions') {
            this.logOffset += this.logLimit;
            this.loadLogs();
        } else {
            this.intentOffset += this.intentLimit;
            this.loadIntents();
        }
    }

    get currentOffset(): number {
        return this.viewMode === 'transactions' ? this.logOffset : this.intentOffset;
    }

    get currentTotal(): number {
        return this.viewMode === 'transactions' ? this.logTotal : this.intentTotal;
    }

    get currentLimit(): number {
        return this.viewMode === 'transactions' ? this.logLimit : this.intentLimit;
    }

    getMetaValue(item: UsageLog, key: string): string {
        if (!item.metadata_) return '';
        const val = item.metadata_[key];
        if (val === null || val === undefined) return '';
        if (typeof val === 'string') return val;
        return JSON.stringify(val, null, 2);
    }

    formatDateTime(dateStr: string): string {
        if (!dateStr) return '—';
        const d = new Date(dateStr);
        return d.toLocaleDateString('fr-CA') + ' ' + d.toLocaleTimeString('fr-CA', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
}
