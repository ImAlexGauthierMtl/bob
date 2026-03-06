import { Component } from '@angular/core';

@Component({
    selector: 'croo-opportunity-profile',
    standalone: true,
    templateUrl: './opportunity-profile.html',
    styleUrl: './opportunity-profile.css',
})
export class OpportunityProfileComponent {
    activeTab = 'overview';

    setActiveTab(tab: string): void {
        this.activeTab = tab;
    }
}
