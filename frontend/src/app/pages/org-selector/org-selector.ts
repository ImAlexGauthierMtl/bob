import { Component, OnInit, inject } from '@angular/core';
import { AuthService } from '../../shared/services/auth.service';
import { BccService } from '../../shared/services/bcc.service';
import { BccOrganization } from '../../shared/models/bcc.model';

@Component({
    selector: 'croo-org-selector',
    standalone: true,
    templateUrl: './org-selector.html',
    styleUrls: ['./org-selector.css'],
})
export class OrgSelectorComponent implements OnInit {
    organizations: BccOrganization[] = [];
    isLoading = true;

    private authService = inject(AuthService);
    private bccService = inject(BccService);

    ngOnInit(): void {
        this.bccService.listOrganizations().subscribe({
            next: (orgs) => {
                this.organizations = orgs;
                this.isLoading = false;
                // If only 1 org, auto-select
                if (orgs.length === 1) {
                    this.selectOrg(orgs[0]);
                }
            },
            error: () => { this.isLoading = false; },
        });
    }

    selectOrg(org: BccOrganization): void {
        this.authService.setActiveOrganization(org.id).subscribe();
    }
}
