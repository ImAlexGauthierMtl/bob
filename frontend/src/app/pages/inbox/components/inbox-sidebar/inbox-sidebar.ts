import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { InboxFilter } from '../../../../shared/models/inbox-filter.model';
import { SmartLabel } from '../../../../shared/models/smart-label.model';
import { loadInboxLabels } from '../../../../store/inbox/inbox.actions';
import { selectInboxLabels } from '../../../../store/inbox/inbox.selectors';

@Component({
    selector: 'app-inbox-sidebar',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './inbox-sidebar.html',
    styleUrl: './inbox-sidebar.css'
})
export class InboxSidebarComponent implements OnInit {

    @Output() composeRequested = new EventEmitter<void>();
    @Output() filterChanged = new EventEmitter<InboxFilter>();

    activeFolder = 'All Mail';
    activeSmartLabel = '';
    
    smartLabels$: Observable<SmartLabel[]>;

    constructor(private store: Store) {
        this.smartLabels$ = this.store.select(selectInboxLabels);
    }

    ngOnInit(): void {
        this.store.dispatch(loadInboxLabels());
    }

    openCompose(): void {
        this.composeRequested.emit();
    }

    setFolder(folder: string): void {
        this.activeFolder = folder;
        this.activeSmartLabel = '';
        this.filterChanged.emit({ folder: folder === 'All Mail' ? '' : folder });
    }

    setSmartLabel(label: string): void {
        this.activeSmartLabel = label;
        this.activeFolder = '';
        this.filterChanged.emit({ smartLabel: label });
    }

    setFilter(filterType: string): void {
        switch (filterType) {
            case 'ai_priority':
                this.activeFolder = '';
                this.activeSmartLabel = '';
                this.filterChanged.emit({ folder: 'inbox', isImportant: true });
                break;
            case 'focus':
                this.activeFolder = '';
                this.activeSmartLabel = '';
                this.filterChanged.emit({ folder: 'inbox', isImportant: true }); // Simplified for now
                break;
            case 'unread_ai':
                this.activeFolder = '';
                this.activeSmartLabel = '';
                this.filterChanged.emit({ folder: 'inbox', isUnread: true });
                break;
            case 'starred':
                this.activeFolder = '';
                this.activeSmartLabel = '';
                this.filterChanged.emit({ folder: 'inbox', isImportant: true });
                break;
            case 'inbox':
                this.setFolder('All Mail');
                break;
            case 'sent':
                this.setFolder('Sent Items');
                break;
            case 'drafts':
                this.setFolder('Drafts');
                break;
            case 'trash':
                this.setFolder('Deleted Items');
                break;
        }
    }
}
