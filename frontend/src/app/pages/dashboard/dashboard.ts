import { Component, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { OrganizationService } from '../../shared/services/organization.service';
import { ContactService } from '../../shared/services/contact.service';
import { OpportunityService } from '../../shared/services/opportunity.service';
import { QuoteService } from '../../shared/services/quote.service';
import { ActivityService } from '../../shared/services/activity.service';

@Component({
    selector: 'croo-dashboard',
    standalone: true,
    imports: [RouterLink],
    templateUrl: './dashboard.html',
    styleUrl: './dashboard.css',
})
export class DashboardComponent implements OnInit {
    orgCount = 0;
    contactCount = 0;
    oppCount = 0;
    quoteCount = 0;
    activityCount = 0;
    isLoading = true;

    constructor(
        private orgService: OrganizationService,
        private contactService: ContactService,
        private oppService: OpportunityService,
        private quoteService: QuoteService,
        private actService: ActivityService,
    ) { }

    ngOnInit(): void {
        this.loadCounts();
    }

    loadCounts(): void {
        this.isLoading = true;
        let loaded = 0;
        const checkDone = () => { loaded++; if (loaded >= 5) this.isLoading = false; };

        this.orgService.list(0, 1).subscribe({ next: (r) => { this.orgCount = r.total; checkDone(); }, error: checkDone });
        this.contactService.list(0, 1).subscribe({ next: (r) => { this.contactCount = r.total; checkDone(); }, error: checkDone });
        this.oppService.list(0, 1).subscribe({ next: (r) => { this.oppCount = r.total; checkDone(); }, error: checkDone });
        this.quoteService.list(0, 1).subscribe({ next: (r) => { this.quoteCount = r.total; checkDone(); }, error: checkDone });
        this.actService.list(0, 1).subscribe({ next: (r) => { this.activityCount = r.total; checkDone(); }, error: checkDone });
    }
}
