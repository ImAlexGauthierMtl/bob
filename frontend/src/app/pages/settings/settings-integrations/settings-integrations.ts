import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MS365Service } from '../../../shared/services/ms365.service';
import { MS365Connection } from '../../../shared/models/ms365.model';

@Component({
    selector: 'croo-settings-integrations',
    standalone: true,
    imports: [CommonModule, RouterLink],
    templateUrl: './settings-integrations.html',
    styleUrls: ['../settings-shared.css'],
})
export class SettingsIntegrationsComponent implements OnInit {
    private ms365Service = inject(MS365Service);

    ms365Connection: MS365Connection | null = null;
    ms365Loading = false;
    ms365Syncing = false;
    ms365Error: string | null = null;

    ngOnInit(): void {
        this.loadMs365Status();

        const params = new URLSearchParams(window.location.search);
        const ms365Status = params.get('ms365');
        if (ms365Status === 'connected') {
            this.loadMs365Status();
            window.history.replaceState({}, '', window.location.pathname);
        } else if (ms365Status === 'error') {
            this.ms365Error = 'Connection to Microsoft 365 failed. Please try again.';
            window.history.replaceState({}, '', window.location.pathname);
        }
    }

    loadMs365Status(): void {
        this.ms365Loading = true;
        this.ms365Error = null;
        this.ms365Service.getConnection().subscribe({
            next: (conn) => {
                this.ms365Connection = conn;
                this.ms365Loading = false;
            },
            error: () => {
                this.ms365Loading = false;
            },
        });
    }

    connectMs365(): void {
        this.ms365Loading = true;
        this.ms365Error = null;
        this.ms365Service.getAuthUrl().subscribe({
            next: (data) => {
                window.location.href = data.auth_url;
            },
            error: (err) => {
                this.ms365Loading = false;
                if (err?.status === 503) {
                    this.ms365Error = 'Microsoft 365 is not configured on this instance. Contact your administrator.';
                } else {
                    this.ms365Error = 'Failed to initiate connection. Please try again.';
                }
            },
        });
    }

    disconnectMs365(): void {
        if (!confirm('Disconnect Microsoft 365? Your synced data will be preserved.')) {
            return;
        }
        this.ms365Loading = true;
        this.ms365Service.disconnect().subscribe({
            next: () => {
                this.ms365Connection = null;
                this.ms365Loading = false;
            },
            error: () => {
                this.ms365Loading = false;
            },
        });
    }

    forceSync(): void {
        this.ms365Syncing = true;
        this.ms365Error = null;
        this.ms365Service.triggerSync().subscribe({
            next: (result) => {
                this.ms365Syncing = false;
                this.loadMs365Status();
            },
            error: () => {
                this.ms365Syncing = false;
                this.ms365Error = 'Sync failed. Your connection may need to be refreshed.';
            },
        });
    }

    get ms365IsConnected(): boolean {
        return !!this.ms365Connection?.is_active;
    }

    get ms365NeedsReauth(): boolean {
        if (!this.ms365Connection) return false;
        return this.ms365Connection.connection_status === 'token_expired'
            || this.ms365Connection.connection_status === 'needs_reauth';
    }
}
