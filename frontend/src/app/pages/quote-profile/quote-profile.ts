import { Component } from '@angular/core';

@Component({
    selector: 'croo-quote-profile',
    standalone: true,
    templateUrl: './quote-profile.html',
    styleUrl: './quote-profile.css',
})
export class QuoteProfileComponent {
    activeTab = 'overview';
}
