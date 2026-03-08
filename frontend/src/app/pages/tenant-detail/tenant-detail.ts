import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { TenantService } from '../../shared/services/tenant.service';
import { Tenant, UpdateTenantDto, ProvisionRequest } from '../../shared/models/tenant.model';
import { environment } from '../../../environments/environment';

interface UsageLog {
    id: string;
    timestamp: string;
    service_type: string;
    provider: string;
    model: string;
    trigger_source: string;
    trigger_id: string;
    input_tokens: number;
    output_tokens: number;
    audio_seconds: number;
    characters: number;
    cogs_amount: number;
    cogs_currency: string;
    user_id: string;
    user_email: string;
    is_billable: boolean;
}

interface UsageListResponse {
    items: UsageLog[];
    total: number;
    skip: number;
    limit: number;
}

@Component({
    selector: 'croo-tenant-detail',
    standalone: true,
    imports: [RouterLink, FormsModule],
    templateUrl: './tenant-detail.html',
    styleUrl: './tenant-detail.css',
})
export class TenantDetailComponent implements OnInit {
    tenant: Tenant | null = null;
    isLoading = true;
    errorMessage = '';
    isSaving = false;
    saveMessage = '';
    saveType: 'success' | 'error' = 'success';

    // Tabs
    activeTab: 'info' | 'logs' = 'info';

    // Provision dialog
    showProvisionDialog = false;
    isProvisioning = false;
    provisionEmail = '';
    provisionPassword = '';
    provisionFirstName = '';
    provisionLastName = '';
    provisionMessage = '';
    provisionType: 'success' | 'error' = 'success';

    // Status change
    showStatusDialog = false;
    newStatus = '';

    // Logs
    logItems: UsageLog[] = [];
    logTotal = 0;
    logTotalCogs = 0;
    logOffset = 0;
    logLimit = 50;
    logFilterService = '';
    logsLoading = false;
    logsLoaded = false;

    Math = Math;

    private tenantService = inject(TenantService);
    private http = inject(HttpClient);
    private route = inject(ActivatedRoute);
    private router = inject(Router);

    ngOnInit(): void {
        const id = this.route.snapshot.paramMap.get('id');
        if (id) {
            this.loadTenant(id);
        }
    }

    loadTenant(id: string): void {
        this.isLoading = true;
        this.tenantService.getById(id).subscribe({
            next: (tenant) => {
                this.tenant = tenant;
                this.isLoading = false;
            },
            error: (err) => {
                this.isLoading = false;
                this.errorMessage = err.status === 404 ? 'Tenant introuvable' : 'Erreur de chargement';
            },
        });
    }

    // ── Tabs ────────────────────────────────────

    switchToLogs(): void {
        this.activeTab = 'logs';
        if (!this.logsLoaded) {
            this.loadLogs();
        }
    }

    // ── Logs ────────────────────────────────────

    loadLogs(): void {
        if (!this.tenant) return;
        this.logsLoading = true;

        let url = `${environment.apiUrl}/admin/usage?tenant_id=${this.tenant.id}&skip=${this.logOffset}&limit=${this.logLimit}`;
        if (this.logFilterService) {
            url += `&service_type=${this.logFilterService}`;
        }

        this.http.get<UsageListResponse>(url).subscribe({
            next: (res) => {
                this.logItems = res.items;
                this.logTotal = res.total;
                this.logTotalCogs = res.items.reduce((sum, i) => sum + (i.cogs_amount || 0), 0);
                this.logsLoading = false;
                this.logsLoaded = true;
            },
            error: () => {
                this.logsLoading = false;
                this.logItems = [];
                this.logTotal = 0;
            },
        });
    }

    formatDateTime(dateStr: string): string {
        if (!dateStr) return '—';
        const d = new Date(dateStr);
        return d.toLocaleDateString('fr-CA') + ' ' + d.toLocaleTimeString('fr-CA', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    // ── Save ────────────────────────────────────

    save(): void {
        if (!this.tenant) return;
        this.isSaving = true;
        this.saveMessage = '';

        const data: UpdateTenantDto = {
            name: this.tenant.name,
            slug: this.tenant.slug,
            owner_email: this.tenant.owner_email,
            owner_name: this.tenant.owner_name,
            plan: this.tenant.plan,
            max_users: this.tenant.max_users,
            notes: this.tenant.notes || undefined,
        };

        this.tenantService.update(this.tenant.id, data).subscribe({
            next: (updated) => {
                this.tenant = updated;
                this.isSaving = false;
                this.saveMessage = '✅ Sauvegardé';
                this.saveType = 'success';
                setTimeout(() => this.saveMessage = '', 3000);
            },
            error: (err) => {
                this.isSaving = false;
                this.saveMessage = `❌ ${err.error?.detail || 'Erreur'}`;
                this.saveType = 'error';
            },
        });
    }

    // ── Status Change ───────────────────────────

    openStatusDialog(): void {
        if (!this.tenant) return;
        this.newStatus = this.tenant.status;
        this.showStatusDialog = true;
    }

    confirmStatusChange(): void {
        if (!this.tenant || this.newStatus === this.tenant.status) {
            this.showStatusDialog = false;
            return;
        }

        this.tenantService.update(this.tenant.id, { status: this.newStatus }).subscribe({
            next: (updated) => {
                this.tenant = updated;
                this.showStatusDialog = false;
                this.saveMessage = `✅ Statut changé à ${this.newStatus}`;
                this.saveType = 'success';
                setTimeout(() => this.saveMessage = '', 3000);
            },
            error: () => {
                this.showStatusDialog = false;
                this.saveMessage = '❌ Erreur changement de statut';
                this.saveType = 'error';
            },
        });
    }

    // ── Provision ───────────────────────────────

    openProvisionDialog(): void {
        this.showProvisionDialog = true;
        this.provisionEmail = '';
        this.provisionPassword = '';
        this.provisionFirstName = '';
        this.provisionLastName = '';
        this.provisionMessage = '';
        this.isProvisioning = false;
    }

    submitProvision(): void {
        if (!this.tenant) return;
        if (!this.provisionEmail.trim() || !this.provisionPassword.trim() ||
            !this.provisionFirstName.trim() || !this.provisionLastName.trim()) return;

        this.isProvisioning = true;
        this.provisionMessage = '';

        const data: ProvisionRequest = {
            admin_email: this.provisionEmail.trim(),
            admin_password: this.provisionPassword.trim(),
            admin_first_name: this.provisionFirstName.trim(),
            admin_last_name: this.provisionLastName.trim(),
        };

        this.tenantService.provision(this.tenant.id, data).subscribe({
            next: (res) => {
                this.isProvisioning = false;
                this.provisionMessage = `✅ ${res.message} — ${res.admin_email}`;
                this.provisionType = 'success';
            },
            error: (err) => {
                this.isProvisioning = false;
                const detail = err.error?.detail;
                const msg = typeof detail === 'string' ? detail
                    : Array.isArray(detail) ? detail.map((d: any) => d.msg).join(', ')
                        : 'Erreur de provisionnement';
                this.provisionMessage = `❌ ${msg}`;
                this.provisionType = 'error';
            },
        });
    }

    // ── Delete ──────────────────────────────────

    deleteTenant(): void {
        if (!this.tenant) return;
        this.tenantService.delete(this.tenant.id).subscribe({
            next: () => this.router.navigate(['/tenants']),
            error: () => {
                this.saveMessage = '❌ Erreur lors de la suppression';
                this.saveType = 'error';
            },
        });
    }

    // ── Helpers ──────────────────────────────────

    getStatusClass(status: string): string {
        switch (status) {
            case 'ACTIVE': return 'status-badge--accent';
            case 'TRIAL': return 'status-badge--warn';
            case 'SUSPENDED': return 'status-badge--danger';
            case 'CANCELLED': return 'status-badge--muted';
            default: return 'status-badge--muted';
        }
    }

    formatDate(dateStr: string | null): string {
        if (!dateStr) return '—';
        return new Date(dateStr).toLocaleDateString('fr-CA');
    }
}
