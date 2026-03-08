import { Component, OnInit, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TenantService } from '../../shared/services/tenant.service';
import { Tenant, CreateTenantDto } from '../../shared/models/tenant.model';

@Component({
    selector: 'croo-tenants',
    standalone: true,
    imports: [RouterLink, FormsModule],
    templateUrl: './tenants.html',
    styleUrl: './tenants.css',
})
export class TenantsComponent implements OnInit {
    tenants: Tenant[] = [];
    total = 0;
    isLoading = true;
    errorMessage = '';

    // Stats
    activeCount = 0;
    trialCount = 0;
    suspendedCount = 0;

    // Filter
    searchQuery = '';
    activeFilter = '';

    // Dialog state
    showAddDialog = false;
    isCreating = false;
    statusMessage = '';
    statusType: 'info' | 'success' | 'error' = 'info';

    // Create form
    newName = '';
    newSlug = '';
    newOwnerEmail = '';
    newOwnerName = '';
    newPlan = 'STARTER';
    newMaxUsers = 5;
    newNotes = '';

    private tenantService = inject(TenantService);
    private router = inject(Router);

    ngOnInit(): void {
        this.loadTenants();
    }

    loadTenants(): void {
        this.isLoading = true;
        this.errorMessage = '';
        this.tenantService.getAll(0, 100, this.searchQuery || undefined, this.activeFilter || undefined).subscribe({
            next: (res) => {
                this.tenants = res.items;
                this.total = res.total;
                this.computeStats();
                this.isLoading = false;
            },
            error: (err) => {
                this.isLoading = false;
                this.errorMessage = err.status === 403
                    ? 'Accès refusé — Super admin requis'
                    : 'Erreur lors du chargement des tenants';
            },
        });
    }

    computeStats(): void {
        this.activeCount = this.tenants.filter(t => t.status === 'ACTIVE').length;
        this.trialCount = this.tenants.filter(t => t.status === 'TRIAL').length;
        this.suspendedCount = this.tenants.filter(t => t.status === 'SUSPENDED').length;
    }

    // ── Filter ──────────────────────────────────

    filterByStatus(status: string): void {
        this.activeFilter = this.activeFilter === status ? '' : status;
        this.loadTenants();
    }

    onSearch(): void {
        this.loadTenants();
    }

    // ── Dialog ──────────────────────────────────

    openAddDialog(): void {
        this.showAddDialog = true;
        this.resetForm();
    }

    closeAddDialog(): void {
        this.showAddDialog = false;
    }

    resetForm(): void {
        this.newName = '';
        this.newSlug = '';
        this.newOwnerEmail = '';
        this.newOwnerName = '';
        this.newPlan = 'STARTER';
        this.newMaxUsers = 5;
        this.newNotes = '';
        this.isCreating = false;
        this.statusMessage = '';
    }

    generateSlug(): void {
        this.newSlug = this.newName
            .toLowerCase()
            .replace(/[^a-z0-9\s-]/g, '')
            .replace(/\s+/g, '-')
            .substring(0, 100);
    }

    submitCreate(): void {
        if (!this.newName.trim() || !this.newSlug.trim() || !this.newOwnerEmail.trim() || !this.newOwnerName.trim()) return;
        this.isCreating = true;
        this.statusMessage = '';

        const data: CreateTenantDto = {
            name: this.newName.trim(),
            slug: this.newSlug.trim(),
            owner_email: this.newOwnerEmail.trim(),
            owner_name: this.newOwnerName.trim(),
            plan: this.newPlan,
            max_users: this.newMaxUsers,
            notes: this.newNotes || undefined,
        };

        this.tenantService.create(data).subscribe({
            next: (tenant) => {
                this.showAddDialog = false;
                this.router.navigate(['/tenants', tenant.id]);
            },
            error: (err) => {
                this.isCreating = false;
                const detail = err.error?.detail || 'Erreur lors de la création';
                this.statusMessage = `❌ ${detail}`;
                this.statusType = 'error';
            },
        });
    }

    // ── Helpers ──────────────────────────────────

    getInitials(name: string): string {
        return name
            .split(' ')
            .map(w => w[0])
            .join('')
            .substring(0, 2)
            .toUpperCase();
    }

    getStatusClass(status: string): string {
        switch (status) {
            case 'ACTIVE': return 'status-badge--accent';
            case 'TRIAL': return 'status-badge--warn';
            case 'SUSPENDED': return 'status-badge--danger';
            case 'CANCELLED': return 'status-badge--muted';
            default: return 'status-badge--muted';
        }
    }

    getPlanLabel(plan: string): string {
        switch (plan) {
            case 'STARTER': return 'Starter';
            case 'PRO': return 'Pro';
            case 'ENTERPRISE': return 'Enterprise';
            default: return plan;
        }
    }

    formatDate(dateStr: string | null): string {
        if (!dateStr) return '—';
        return new Date(dateStr).toLocaleDateString('fr-CA');
    }
}
