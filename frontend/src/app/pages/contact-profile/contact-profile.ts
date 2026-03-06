import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'croo-contact-profile',
    standalone: true,
    imports: [RouterLink],
    templateUrl: './contact-profile.html',
    styleUrl: './contact-profile.css',
})
export class ContactProfileComponent {
    activeTab = 'overview';

    setActiveTab(tab: string): void {
        this.activeTab = tab;
    }
}
