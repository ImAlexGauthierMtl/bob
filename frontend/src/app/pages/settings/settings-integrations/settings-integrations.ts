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

    ngOnInit(): void {
        this.loadMs365Status();

        // Check for OAuth callback result
        const params = new URLSearchParams(window.location.search);
        const ms365Status = params.get('ms365');
        if (ms365Status === 'connected') {
            this.loadMs365Status();
            // Clean URL
            window.history.replaceState({}, '', window.location.pathname);
        }
    }

    loadMs365Status(): void {
        this.ms365Loading = true;
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
        this.ms365Service.getAuthUrl().subscribe({
            next: (data) => {
                window.location.href = data.auth_url;
            },
            error: () => {
                this.ms365Loading = false;
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
        this.ms365Service.triggerSync().subscribe({
            next: (result) => {
                this.ms365Syncing = false;
                this.loadMs365Status();
            },
            error: () => {
                this.ms365Syncing = false;
            },
        });
    }

    get ms365IsConnected(): boolean {
        return !!this.ms365Connection?.is_active;
    }
}
