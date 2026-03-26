import { Component, EventEmitter, OnInit, Output, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { SyncedEmail, MS365Connection } from '../../../../shared/models/ms365.model';
import { MS365Service } from '../../../../shared/services/ms365.service';
import { finalize } from 'rxjs';
import { InboxFilter } from '../inbox-sidebar/inbox-sidebar';

@Component({
    selector: 'app-email-list',
    standalone: true,
    imports: [CommonModule, RouterLink],
    templateUrl: './email-list.html',
    styleUrl: './email-list.css'
})
export class EmailListComponent implements OnInit {

    @Output() emailSelected = new EventEmitter<SyncedEmail>();

    @Input() set filter(val: InboxFilter) {
        if (!val) return;
        this.currentFolder = val.folder || '';
        this.currentSearch = '';
        this.currentSmartLabel = val.smartLabel || '';
        if (this.initialized) {
            this.loadEmails(true);
        }
    }

    emails: SyncedEmail[] = [];
    isLoading = false;
    total = 0;
    skip = 0;
    limit = 50;
    selectedEmailId: string | null = null;
    
    currentFolder = '';
    currentSearch = '';
    currentSmartLabel = '';
    initialized = false;

    ms365Connection: MS365Connection | null = null;
    connectionChecked = false;

    constructor(private ms365Service: MS365Service) {}

    ngOnInit(): void {
        this.initialized = true;
        this.checkConnection();
        this.loadEmails();
    }

    checkConnection(): void {
        this.ms365Service.getConnection().subscribe({
            next: (conn) => {
                this.ms365Connection = conn;
                this.connectionChecked = true;
            },
            error: () => {
                this.connectionChecked = true;
            },
        });
    }

    get showConnectionBanner(): boolean {
        if (!this.connectionChecked) return false;
        if (!this.ms365Connection) return true;
        return !this.ms365Connection.is_active
            || this.ms365Connection.connection_status === 'token_expired'
            || this.ms365Connection.connection_status === 'needs_reauth';
    }

    get connectionBannerMessage(): string {
        if (!this.ms365Connection) {
            return 'Connect your Microsoft 365 account to sync your emails.';
        }
        return 'Your Microsoft 365 connection needs to be refreshed.';
    }

    loadEmails(reset = false): void {
        if (this.isLoading) return;
        
        if (reset) {
            this.skip = 0;
            this.emails = [];
        }

        this.isLoading = true;
        this.ms365Service.getEmails(this.skip, this.limit, this.currentFolder, this.currentSearch, this.currentSmartLabel)
            .pipe(finalize(() => this.isLoading = false))
            .subscribe({
                next: (res) => {
                    this.emails = reset ? res.items : [...this.emails, ...res.items];
                    this.total = res.total;
                },
                error: (err) => console.error('Failed to load emails', err)
            });
    }

    onScroll(event: Event): void {
        const target = event.target as HTMLElement;
        const offset = 150;
        if (target.scrollHeight - target.scrollTop <= target.clientHeight + offset) {
            this.loadMore();
        }
    }

    loadMore(): void {
        if (this.emails.length < this.total) {
            this.skip += this.limit;
            this.loadEmails();
        }
    }

    selectEmail(email: SyncedEmail): void {
        this.selectedEmailId = email.id;
        email.is_read = true;
        this.emailSelected.emit(email);
    }
    
    parseSmartLabel(label: string): string[] {
        if (!label) return [];
        return label.split(' > ').map(p => p.trim());
    }
}
