import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface InboxFilter {
    folder?: string;
    smartLabel?: string;
    isUnread?: boolean;
    isImportant?: boolean;
}

import { SmartLabel } from '../../../../shared/models/smart-label.model';
import { SmartLabelService } from '../../../../shared/services/smart-label.service';

@Component({
    selector: 'app-inbox-sidebar',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './inbox-sidebar.html',
    styleUrl: './inbox-sidebar.css'
})
export class InboxSidebarComponent implements OnInit {

    @Output() filterChanged = new EventEmitter<InboxFilter>();

    activeFolder = 'All Mail';
    activeSmartLabel = '';
    
    smartLabels: SmartLabel[] = [];

    constructor(private smartLabelService: SmartLabelService) {}

    ngOnInit(): void {
        this.loadLabels();
    }

    loadLabels(): void {
        this.smartLabelService.getAll(0, 50).subscribe({
            next: (res) => {
                this.smartLabels = res.items;
            },
            error: (err) => console.error('Failed to load smart labels in sidebar', err)
        });
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
