import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MS365Service } from '../../../shared/services/ms365.service';
import { MS365Connection, SyncedEmail, SyncedEvent } from '../../../shared/models/ms365.model';

@Component({
    selector: 'croo-settings-ms365',
    standalone: true,
    imports: [CommonModule, RouterLink],
    templateUrl: './settings-ms365.html',
    styleUrls: ['../settings-shared.css'],
})
export class SettingsMs365Component implements OnInit {
    private ms365Service = inject(MS365Service);

    connection: MS365Connection | null = null;
    emails: SyncedEmail[] = [];
    events: SyncedEvent[] = [];
    activeTab: 'emails' | 'calendar' = 'emails';
    syncing = false;
    loading = true;
    emailTotal = 0;
    eventTotal = 0;

    ngOnInit(): void {
        this.loadConnection();
        this.loadEmails();
        this.loadEvents();
    }

    loadConnection(): void {
        this.ms365Service.getConnection().subscribe({
            next: (conn) => {
                this.connection = conn;
                this.loading = false;
            },
            error: () => { this.loading = false; },
        });
    }

    loadEmails(): void {
        this.ms365Service.getEmails(0, 20).subscribe({
            next: (res) => {
                this.emails = res.items;
                this.emailTotal = res.total;
            },
        });
    }

    loadEvents(): void {
        this.ms365Service.getEvents(0, 20).subscribe({
            next: (res) => {
                this.events = res.items;
                this.eventTotal = res.total;
            },
        });
    }

    forceSync(): void {
        this.syncing = true;
        this.ms365Service.triggerSync().subscribe({
            next: () => {
                this.syncing = false;
                this.loadConnection();
                this.loadEmails();
                this.loadEvents();
            },
            error: () => { this.syncing = false; },
        });
    }

    setTab(tab: 'emails' | 'calendar'): void {
        this.activeTab = tab;
    }

    formatDate(iso: string | null): string {
        if (!iso) return '—';
        return new Date(iso).toLocaleString();
    }

    disconnect(): void {
        if (!confirm('Disconnect Microsoft 365?')) return;

        this.ms365Service.disconnect().subscribe({
            next: () => {
                this.connection = null;
            },
        });
    }
}
