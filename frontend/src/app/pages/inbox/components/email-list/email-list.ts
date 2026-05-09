import { Component, EventEmitter, OnInit, Output, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { UnifiedEmail, UnifiedConnection } from '../../../../shared/models/unified-email.model';
import { EmailService } from '../../../../shared/services/email.service';
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

    @Output() emailSelected = new EventEmitter<UnifiedEmail>();

    @Input() set filter(val: InboxFilter) {
        if (!val) return;
        this.currentFolder = val.folder || '';
        this.currentSearch = '';
        this.currentSmartLabel = val.smartLabel || '';
        if (this.initialized) {
            this.loadEmails(true);
        }
    }

    emails: UnifiedEmail[] = [];
    isLoading = false;
    total = 0;
    skip = 0;
    limit = 50;
    selectedEmailId: string | null = null;
    
    currentFolder = '';
    currentSearch = '';
    currentSmartLabel = '';
    initialized = false;

    emailConnection: UnifiedConnection | null = null;
    connectionChecked = false;

    constructor(private emailService: EmailService) {}

    ngOnInit(): void {
        this.initialized = true;
        this.checkConnection();
        this.loadEmails();
    }

    checkConnection(): void {
        this.emailService.getConnection().subscribe({
            next: (conn) => {
                this.emailConnection = conn;
                this.connectionChecked = true;
            },
            error: () => {
                this.connectionChecked = true;
            },
        });
    }

    get showConnectionBanner(): boolean {
        if (!this.connectionChecked) return false;
        if (!this.emailConnection) return true;
        return !this.emailConnection.isActive
            || this.emailConnection.status === 'token_expired'
            || this.emailConnection.status === 'needs_reauth';
    }

    get connectionBannerMessage(): string {
        if (!this.emailConnection) {
            return 'Connect your email account via Settings > Integrations to sync your emails.';
        }
        return 'Your email connection needs to be refreshed. Go to Settings > Integrations.';
    }

    loadEmails(reset = false): void {
        if (this.isLoading) return;
        
        if (reset) {
            this.skip = 0;
            this.emails = [];
        }

        this.isLoading = true;
        this.emailService.getEmails(this.skip, this.limit, this.currentFolder, this.currentSearch, this.currentSmartLabel)
            .pipe(finalize(() => this.isLoading = false))
            .subscribe({
                next: (res) => {
                    this.emails = reset ? res.items : [...this.emails, ...res.items];
                    this.total = res.total;
                },
                error: (err) => console.error('Failed to load emails', err)
            });
    }

    onRefresh(): void {
        // Trigger background sync then reload
        this.emailService.triggerSync().subscribe({
            next: () => this.loadEmails(true),
            error: () => this.loadEmails(true) // load anyway even if sync fails
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

    selectEmail(email: UnifiedEmail): void {
        this.selectedEmailId = email.id;
        email.is_read = true;
        this.emailSelected.emit(email);
    }
    
    parseSmartLabel(label: string): string[] {
        if (!label) return [];
        return label.split(' > ').map(p => p.trim());
    }
}
