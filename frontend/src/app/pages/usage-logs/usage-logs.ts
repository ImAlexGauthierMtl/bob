import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { IntentGroup, UsageLog, UsageService } from '../../shared/services/usage.service';

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

    private usageService = inject(UsageService);

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
        this.usageService.listUsage({
            skip: this.logOffset,
            limit: this.logLimit,
            serviceType: this.filterService || undefined,
            tenantId: this.filterTenant || undefined,
        }).subscribe({
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
        this.usageService.listIntents({
            skip: this.intentOffset,
            limit: this.intentLimit,
            tenantId: this.filterTenant || undefined,
        }).subscribe({
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

        this.usageService.getIntentUsage(intent.correlation_id).subscribe({
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
