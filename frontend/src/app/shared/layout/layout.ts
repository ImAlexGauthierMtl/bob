import { Component, OnInit } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { BobChatComponent } from '../bob-chat/bob-chat';
import { BobDisplayOverlayComponent } from '../bob-display-overlay/bob-display-overlay';
import { AuthService } from '../services/auth.service';
import { BccService } from '../services/bcc.service';
import { BccOrganization } from '../models/bcc.model';

@Component({
    selector: 'croo-layout',
    standalone: true,
    imports: [RouterOutlet, RouterLink, RouterLinkActive, BobChatComponent, BobDisplayOverlayComponent],
    templateUrl: './layout.html',
    styleUrl: './layout.css',
})
export class LayoutComponent implements OnInit {
    userName = '';
    userRole = '';
    isSuperAdmin = false;
    activeOrgName: string | null = null;
    activeOrgId: string | null = null;
    showOrgDropdown = false;
    organizations: BccOrganization[] = [];

    constructor(
        private authService: AuthService,
        private bccService: BccService,
    ) { }

    ngOnInit(): void {
        this.authService.getCurrentUser().subscribe({
            next: (user) => {
                if (!user) {
                    this.userName = 'User';
                    this.userRole = '';
                    return;
                }
                this.userName = `${user.first_name} ${user.last_name}`;
                this.userRole = user.role || '';
                this.isSuperAdmin = !!user.is_super_admin;
                this.activeOrgName = user.active_organization_name;
                this.activeOrgId = user.active_organization_id;
            },
            error: () => {
                this.userName = 'User';
                this.userRole = '';
            },
        });
        this.bccService.listOrganizations().subscribe({
            next: (orgs) => this.organizations = orgs,
        });
    }

    toggleOrgDropdown(): void {
        this.showOrgDropdown = !this.showOrgDropdown;
    }

    switchOrg(org: BccOrganization): void {
        this.showOrgDropdown = false;
        this.authService.setActiveOrganization(org.id).subscribe({
            next: (user) => {
                this.activeOrgName = user.active_organization_name;
                this.activeOrgId = user.active_organization_id;
            },
        });
    }
}
