import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { InboxSidebarComponent, InboxFilter } from './components/inbox-sidebar/inbox-sidebar';
import { EmailListComponent } from './components/email-list/email-list';
import { EmailReadingPaneComponent } from './components/email-reading-pane/email-reading-pane';
import { EmailComposeComponent } from './components/email-compose/email-compose';

import { UnifiedEmail } from '../../shared/models/unified-email.model';

@Component({
    selector: 'app-inbox-overview',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        InboxSidebarComponent,
        EmailListComponent,
        EmailReadingPaneComponent,
        EmailComposeComponent
    ],
    templateUrl: './inbox-overview.html',
    styleUrl: './inbox-overview.css'
})
export class InboxOverviewComponent implements OnInit {

    selectedEmail: UnifiedEmail | null = null;
    currentFilter: InboxFilter = {};
    isComposeOpen = false;

    @ViewChild(EmailListComponent) emailList!: EmailListComponent;

    constructor() {}

    ngOnInit(): void {
    }

    onFilterChanged(filter: InboxFilter): void {
        this.currentFilter = filter;
        this.selectedEmail = null; // reset selection when changing folder
    }

    onEmailSelected(email: UnifiedEmail): void {
        this.selectedEmail = email;
    }

    openCompose(): void {
        this.isComposeOpen = true;
    }

    closeCompose(): void {
        this.isComposeOpen = false;
    }

    onEmailSent(): void {
        this.closeCompose();
        this.emailList?.loadEmails(true);
    }

    onEmailActionCompleted(): void {
        this.emailList?.loadEmails(true);
    }
}
