import { Component, EventEmitter, OnInit, Output, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { InboxFilter } from '../../../../shared/models/inbox-filter.model';
import { UnifiedEmail } from '../../../../shared/models/unified-email.model';
import { loadInboxConnection, loadInboxEmails, loadMoreInboxEmails, refreshInboxEmails } from '../../../../store/inbox/inbox.actions';
import {
    selectInboxConnectionBannerMessage,
    selectInboxEmails,
    selectInboxLoadingEmails,
    selectInboxRangeText,
    selectInboxShowConnectionBanner,
    selectInboxTotal,
} from '../../../../store/inbox/inbox.selectors';

@Component({
    selector: 'app-email-list',
    standalone: true,
    imports: [CommonModule, RouterLink],
    templateUrl: './email-list.html',
    styleUrl: './email-list.css'
})
export class EmailListComponent implements OnInit {

    @Output() emailSelected = new EventEmitter<UnifiedEmail>();

    @Input() set filter(val: InboxFilter) {
        if (!val) return;
    }

    emails$: Observable<UnifiedEmail[]>;
    isLoading$: Observable<boolean>;
    total$: Observable<number>;
    rangeText$: Observable<string>;
    showConnectionBanner$: Observable<boolean>;
    connectionBannerMessage$: Observable<string>;
    selectedEmailId: string | null = null;
    initialized = false;

    constructor(private store: Store) {
        this.emails$ = this.store.select(selectInboxEmails);
        this.isLoading$ = this.store.select(selectInboxLoadingEmails);
        this.total$ = this.store.select(selectInboxTotal);
        this.rangeText$ = this.store.select(selectInboxRangeText);
        this.showConnectionBanner$ = this.store.select(selectInboxShowConnectionBanner);
        this.connectionBannerMessage$ = this.store.select(selectInboxConnectionBannerMessage);
    }

    ngOnInit(): void {
        this.initialized = true;
        this.store.dispatch(loadInboxConnection());
        this.store.dispatch(loadInboxEmails({ reset: true }));
    }

    onRefresh(): void {
        this.store.dispatch(refreshInboxEmails());
    }

    onScroll(event: Event): void {
        const target = event.target as HTMLElement;
        const offset = 150;
        if (target.scrollHeight - target.scrollTop <= target.clientHeight + offset) {
            this.loadMore();
        }
    }

    loadMore(): void {
        this.store.dispatch(loadMoreInboxEmails());
    }

    selectEmail(email: UnifiedEmail): void {
        this.selectedEmailId = email.id;
        this.emailSelected.emit({ ...email, is_read: true });
    }
    
    parseSmartLabel(label: string): string[] {
        if (!label) return [];
        return label.split(' > ').map(p => p.trim());
    }
}
