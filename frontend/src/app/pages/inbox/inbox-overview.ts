import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { InboxFilter } from '../../shared/models/inbox-filter.model';
import { UnifiedEmail } from '../../shared/models/unified-email.model';
import {
    clearInboxSelectedEmail,
    loadInboxEmails,
    selectInboxEmail,
    setInboxFilter,
} from '../../store/inbox/inbox.actions';
import { selectInboxSelectedEmail } from '../../store/inbox/inbox.selectors';
import { InboxSidebarComponent } from './components/inbox-sidebar/inbox-sidebar';
import { EmailListComponent } from './components/email-list/email-list';
import { EmailReadingPaneComponent } from './components/email-reading-pane/email-reading-pane';
import { EmailComposeComponent } from './components/email-compose/email-compose';

@Component({
    selector: 'app-inbox-overview',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        RouterLink,
        InboxSidebarComponent,
        EmailListComponent,
        EmailReadingPaneComponent,
        EmailComposeComponent
    ],
    templateUrl: './inbox-overview.html',
    styleUrl: './inbox-overview.css'
})
export class InboxOverviewComponent implements OnInit {

    selectedEmail$: Observable<UnifiedEmail | null>;
    currentFilter: InboxFilter = {};
    isComposeOpen = false;

    constructor(private store: Store) {
        this.selectedEmail$ = this.store.select(selectInboxSelectedEmail);
    }

    ngOnInit(): void {
    }

    onFilterChanged(filter: InboxFilter): void {
        this.currentFilter = filter;
        this.store.dispatch(setInboxFilter({ filter }));
    }

    onEmailSelected(email: UnifiedEmail): void {
        this.store.dispatch(selectInboxEmail({ email }));
    }

    clearSelectedEmail(): void {
        this.store.dispatch(clearInboxSelectedEmail());
    }

    openCompose(): void {
        this.isComposeOpen = true;
    }

    closeCompose(): void {
        this.isComposeOpen = false;
    }

    onEmailSent(): void {
        this.closeCompose();
        this.store.dispatch(loadInboxEmails({ reset: true }));
    }

    onEmailActionCompleted(): void {
        this.store.dispatch(loadInboxEmails({ reset: true }));
    }
}
