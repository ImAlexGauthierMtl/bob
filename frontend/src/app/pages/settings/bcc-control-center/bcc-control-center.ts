import { Component, OnInit, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { BccService } from '../../../shared/services/bcc.service';
import { BccOrganization, BccIndustry, BccCareer, CognitiveMapDomain } from '../../../shared/models/bcc.model';

@Component({
    selector: 'croo-bcc-control-center',
    standalone: true,
    imports: [RouterLink, FormsModule],
    templateUrl: './bcc-control-center.html',
    styleUrls: [
        '../settings-shared.css',
        '../../organization-detail/organization-detail.css',
        './bcc-control-center.css',
    ],
})
export class BccControlCenterComponent implements OnInit {
    organizations: BccOrganization[] = [];
    industries: BccIndustry[] = [];
    careers: BccCareer[] = [];
    cognitiveMap: CognitiveMapDomain[] = [];
    expandedDomains: Set<string> = new Set();
    expandedIntents: Set<string> = new Set();
    isLoading = true;
    activeTab = 'cognitive';

    // Dialog
    showAddDialog = false;
    newOrgName = '';
    newOrgDesc = '';
    isCreating = false;

    private bccService = inject(BccService);
    private router = inject(Router);

    ngOnInit(): void {
        this.loadAll();
    }

    loadAll(): void {
        this.isLoading = true;
        // Load organizations
        this.bccService.listOrganizations().subscribe({
            next: (orgs) => {
                this.organizations = orgs;
                this.isLoading = false;
            },
            error: () => { this.isLoading = false; },
        });
        // Load library tabs (parallel)
        this.bccService.listIndustries().subscribe({ next: (d) => this.industries = d });
        this.bccService.listCareers().subscribe({ next: (d) => this.careers = d });
        // Load cognitive map
        this.bccService.getCognitiveMap().subscribe({
            next: (map) => {
                this.cognitiveMap = map;
                if (map.length > 0) {
                    this.expandedDomains.add(map[0].id);
                }
            },
        });
    }

    setActiveTab(tab: string): void {
        this.activeTab = tab;
    }

    toggleDomain(domainId: string): void {
        if (this.expandedDomains.has(domainId)) {
            this.expandedDomains.delete(domainId);
        } else {
            this.expandedDomains.add(domainId);
        }
    }

    toggleIntent(intentId: string): void {
        if (this.expandedIntents.has(intentId)) {
            this.expandedIntents.delete(intentId);
        } else {
            this.expandedIntents.add(intentId);
        }
    }

    get cognitiveStats(): { domains: number; intents: number; tasks: number; tools: number; workflows: number } {
        const tools = new Set<string>();
        const workflows = new Set<string>();
        let intents = 0;
        let tasks = 0;
        for (const d of this.cognitiveMap) {
            intents += d.intents.length;
            for (const i of d.intents) {
                if (i.workflow_key) workflows.add(i.workflow_key);
                tasks += i.tasks.length;
                for (const t of i.tasks) {
                    if (t.tool_name) tools.add(t.tool_name);
                }
            }
        }
        return { domains: this.cognitiveMap.length, intents, tasks, tools: tools.size, workflows: workflows.size };
    }

    // Dialog
    openAddDialog(): void {
        this.showAddDialog = true;
        this.newOrgName = '';
        this.newOrgDesc = '';
    }

    closeAddDialog(): void {
        this.showAddDialog = false;
    }

    createOrganization(): void {
        if (!this.newOrgName.trim()) return;
        this.isCreating = true;
        this.bccService.createOrganization({
            name: this.newOrgName.trim(),
            description: this.newOrgDesc.trim() || undefined,
        }).subscribe({
            next: (org) => {
                this.showAddDialog = false;
                this.isCreating = false;
                this.router.navigate(['/settings/bob-control-center', org.id]);
            },
            error: () => { this.isCreating = false; },
        });
    }
}
