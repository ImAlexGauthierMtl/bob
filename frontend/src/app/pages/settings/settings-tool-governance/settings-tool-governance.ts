import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ToolGovernancePolicy, ToolGovernancePolicyListResponse } from '../../../shared/models/tool-governance.model';
import { ToolGovernanceService } from '../../../shared/services/tool-governance.service';

@Component({
    selector: 'croo-settings-tool-governance',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './settings-tool-governance.html',
    styleUrls: ['../settings-shared.css', './settings-tool-governance.css'],
})
export class SettingsToolGovernanceComponent implements OnInit {
    private toolGovernance = inject(ToolGovernanceService);

    response: ToolGovernancePolicyListResponse | null = null;
    loading = false;
    error: string | null = null;
    success: string | null = null;
    searchQuery = '';
    providerFilter = 'all';
    savingById: Record<string, boolean> = {};

    ngOnInit(): void {
        this.load();
    }

    load(): void {
        this.loading = true;
        this.error = null;
        this.toolGovernance.listPolicies().subscribe({
            next: (response) => {
                this.response = response;
                this.loading = false;
            },
            error: () => {
                this.error = 'Unable to load tool governance policies.';
                this.loading = false;
            },
        });
    }

    get policies(): ToolGovernancePolicy[] {
        const policies = this.response?.items || [];
        const query = this.searchQuery.trim().toLowerCase();
        return policies
            .filter((policy) => this.providerFilter === 'all' || policy.provider === this.providerFilter)
            .filter((policy) => {
                if (!query) return true;
                return `${policy.display_name} ${policy.provider} ${policy.family || ''} ${policy.capability || ''} ${policy.tool_key || ''}`
                    .toLowerCase()
                    .includes(query);
            })
            .slice(0, 120);
    }

    get providers(): string[] {
        return Array.from(new Set((this.response?.items || []).map((policy) => policy.provider))).sort();
    }

    savePolicy(policy: ToolGovernancePolicy, changes: Partial<ToolGovernancePolicy>): void {
        const payload = { ...policy, ...changes };
        this.savingById[policy.id] = true;
        this.error = null;
        this.success = null;
        this.toolGovernance.updatePolicy(policy.id, payload).subscribe({
            next: (updated) => {
                this.replacePolicy(updated);
                this.savingById[policy.id] = false;
                this.success = 'Policy saved.';
            },
            error: () => {
                this.savingById[policy.id] = false;
                this.error = 'Unable to save this policy.';
            },
        });
    }

    saveTeamScope(policy: ToolGovernancePolicy, value: string): void {
        const teamScope = value
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean);
        this.savePolicy(policy, { team_scope: teamScope });
    }

    saveNotes(policy: ToolGovernancePolicy, notes: string): void {
        this.savePolicy(policy, { notes });
    }

    teamScopeValue(policy: ToolGovernancePolicy): string {
        return policy.team_scope.join(', ');
    }

    riskClass(risk: string): string {
        if (risk === 'read') return 'status-badge--green';
        if (risk === 'draft') return 'status-badge--blue';
        if (risk === 'destructive-confirmed') return 'status-badge--gray';
        return 'status-badge--purple';
    }

    private replacePolicy(updated: ToolGovernancePolicy): void {
        if (!this.response) return;
        const items = this.response.items.map((policy) => policy.id === updated.id ? updated : policy);
        this.response = {
            ...this.response,
            items,
            enabled_total: items.filter((policy) => policy.enabled).length,
        };
    }
}
