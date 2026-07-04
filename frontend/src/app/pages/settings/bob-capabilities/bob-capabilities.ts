import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { WorkflowService } from '../../../shared/services/workflow.service';
import { UserCapabilities, UserCapability } from '../../../shared/models/workflow.model';

@Component({
    selector: 'croo-bob-capabilities',
    standalone: true,
    imports: [RouterLink, FormsModule],
    templateUrl: './bob-capabilities.html',
    styleUrls: ['../settings-shared.css'],
})
export class BobCapabilitiesComponent implements OnInit {
    capabilities: UserCapability[] = [];
    agentMode = '';
    trustScore = 0;
    isLoading = true;
    searchQuery = '';

    private workflowService = inject(WorkflowService);

    ngOnInit(): void {
        this.loadCapabilities();
    }

    loadCapabilities(): void {
        this.isLoading = true;
        this.workflowService.getMyCapabilities().subscribe({
            next: (data: UserCapabilities) => {
                this.capabilities = data.capabilities;
                this.agentMode = data.agent_mode;
                this.trustScore = data.trust_score;
                this.isLoading = false;
            },
            error: () => {
                this.isLoading = false;
            },
        });
    }

    get filteredCapabilities(): UserCapability[] {
        if (!this.searchQuery.trim()) return this.capabilities;
        const q = this.searchQuery.toLowerCase();
        return this.capabilities.filter(c =>
            c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q)
        );
    }

    get grantedCount(): number {
        return this.capabilities.filter(c => c.granted).length;
    }

    getRiskClass(level: string): string {
        switch (level) {
            case 'low': return 'cap-risk--low';
            case 'medium': return 'cap-risk--medium';
            case 'high': return 'cap-risk--high';
            case 'critical': return 'cap-risk--critical';
            default: return 'cap-risk--low';
        }
    }

    getRiskIcon(level: string): string {
        switch (level) {
            case 'low': return 'fa-solid fa-shield';
            case 'medium': return 'fa-solid fa-shield-halved';
            case 'high': return 'fa-solid fa-triangle-exclamation';
            case 'critical': return 'fa-solid fa-skull-crossbones';
            default: return 'fa-solid fa-shield';
        }
    }

    getScopeIcon(scope: string): string {
        switch (scope) {
            case 'read': return 'fa-solid fa-eye';
            case 'write': return 'fa-solid fa-pen';
            case 'execute': return 'fa-solid fa-play';
            case 'admin': return 'fa-solid fa-crown';
            default: return 'fa-solid fa-circle';
        }
    }
}
