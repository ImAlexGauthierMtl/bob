import { Component, OnInit, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { BccService } from '../../../shared/services/bcc.service';
import { BccOrganization, BccIndustry, BccCareer, BccSkillTemplate, BccTaskTemplate, BccIntent } from '../../../shared/models/bcc.model';

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
    skillTemplates: BccSkillTemplate[] = [];
    taskTemplates: BccTaskTemplate[] = [];
    intents: BccIntent[] = [];
    isLoading = true;
    activeTab = 'organizations';

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
        this.bccService.listSkillTemplates().subscribe({ next: (d) => this.skillTemplates = d });
        this.bccService.listTaskTemplates().subscribe({ next: (d) => this.taskTemplates = d });
        this.bccService.listIntents().subscribe({ next: (d) => this.intents = d });
    }

    setActiveTab(tab: string): void {
        this.activeTab = tab;
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
