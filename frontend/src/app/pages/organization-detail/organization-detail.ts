import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'croo-organization-detail',
    standalone: true,
    imports: [RouterLink],
    templateUrl: './organization-detail.html',
    styleUrl: './organization-detail.css',
})
export class OrganizationDetailComponent {
    activeTab = 'overview';

    setActiveTab(tab: string): void {
        this.activeTab = tab;
    }
}
