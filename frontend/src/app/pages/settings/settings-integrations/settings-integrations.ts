import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MS365Service } from '../../../shared/services/ms365.service';
import { MembraneService } from '../../../shared/services/membrane.service';
import { MS365Connection } from '../../../shared/models/ms365.model';
import { MembraneConnection, MembraneIntegration } from '../../../shared/models/membrane.model';

type IntegrationViewModel = {
    key: string;
    name: string;
    iconClass: string;
    iconColorClass: string;
    description: string;
    connection?: MembraneConnection;
    isLegacyMs365?: boolean;
};

@Component({
    selector: 'croo-settings-integrations',
    standalone: true,
    imports: [CommonModule, RouterLink],
    templateUrl: './settings-integrations.html',
    styleUrls: ['../settings-shared.css'],
})
export class SettingsIntegrationsComponent implements OnInit {
    private ms365Service = inject(MS365Service);
    private membraneService = inject(MembraneService);

    // Legacy MS365 state
    ms365Connection: MS365Connection | null = null;
    ms365Loading = false;
    ms365Syncing = false;
    ms365Error: string | null = null;

    // Membrane state
    membraneConnections: MembraneConnection[] = [];
    membraneIntegrations: MembraneIntegration[] = [];
    membraneLoading = false;
    membraneError: string | null = null;
    searchQuery = '';

    get connectedIntegrations(): IntegrationViewModel[] {
        const connected: IntegrationViewModel[] = [];
        // Legacy MS365 (during transition)
        if (this.ms365IsConnected) {
            connected.push({
                key: 'microsoft-365',
                name: 'Microsoft 365',
                iconClass: 'fa-brands fa-microsoft',
                iconColorClass: 'integration-card__icon--ms',
                description: this.ms365Connection?.ms_email || 'Outlook, Calendar',
                isLegacyMs365: true,
            });
        }
        // Membrane connections
        for (const conn of this.membraneConnections) {
            if (conn.disconnected) continue;
            const integration = this.membraneIntegrations.find(i => i.key === conn.integration_key || i.id === conn.integration_id);
            connected.push({
                key: conn.integration_key,
                name: integration?.name || conn.name || conn.integration_key,
                iconClass: this._iconForIntegration(conn.integration_key),
                iconColorClass: this._colorClassForIntegration(conn.integration_key),
                description: conn.name,
                connection: conn,
            });
        }
        return connected;
    }

    get availableIntegrations(): IntegrationViewModel[] {
        const connectedKeys = new Set(this.connectedIntegrations.map(i => i.key));
        const available: IntegrationViewModel[] = [];

        // Membrane integrations not yet connected
        for (const integration of this.membraneIntegrations) {
            if (!connectedKeys.has(integration.key)) {
                available.push({
                    key: integration.key,
                    name: integration.name,
                    iconClass: this._iconForIntegration(integration.key),
                    iconColorClass: this._colorClassForIntegration(integration.key),
                    description: integration.description || this._defaultDescription(integration.key),
                });
            }
        }

        // Hardcoded available integrations (fallback during Membrane setup)
        const hardcoded = [
            { key: 'hubspot', name: 'HubSpot', iconClass: 'fa-brands fa-hubspot', iconColorClass: 'integration-card__icon--orange', description: 'Sync contacts and marketing campaigns with HubSpot' },
            { key: 'salesforce', name: 'Salesforce', iconClass: 'fa-brands fa-salesforce', iconColorClass: 'integration-card__icon--sf', description: 'Bi-directional sync with Salesforce CRM data' },
            { key: 'mailchimp', name: 'Mailchimp', iconClass: 'fa-brands fa-mailchimp', iconColorClass: 'integration-card__icon--mc', description: 'Manage email campaigns and subscriber lists' },
            { key: 'stripe', name: 'Stripe', iconClass: 'fa-brands fa-stripe', iconColorClass: 'integration-card__icon--indigo', description: 'Process payments and manage subscriptions' },
            { key: 'github', name: 'GitHub', iconClass: 'fa-brands fa-github', iconColorClass: 'integration-card__icon--github', description: 'Link development work to opportunities and projects' },
        ];
        for (const h of hardcoded) {
            if (!connectedKeys.has(h.key)) {
                available.push(h);
            }
        }

        // Legacy MS365 available (during transition)
        if (!this.ms365IsConnected) {
            available.unshift({
                key: 'microsoft-outlook',
                name: 'Microsoft 365',
                iconClass: 'fa-brands fa-microsoft',
                iconColorClass: 'integration-card__icon--ms',
                description: 'Emails, contacts & calendar on two-way sync.',
            });
        }

        // Filter by search
        if (this.searchQuery.trim()) {
            const q = this.searchQuery.toLowerCase();
            return available.filter(i => i.name.toLowerCase().includes(q) || i.description.toLowerCase().includes(q));
        }
        return available;
    }

    ngOnInit(): void {
        this.loadMs365Status();
        this.loadMembraneData();

        const params = new URLSearchParams(window.location.search);
        const ms365Status = params.get('ms365');
        if (ms365Status === 'connected') {
            this.loadMs365Status();
            window.history.replaceState({}, '', window.location.pathname);
        } else if (ms365Status === 'error') {
            this.ms365Error = 'Connection to Microsoft 365 failed. Please try again.';
            window.history.replaceState({}, '', window.location.pathname);
        }

        // Membrane callback
        const membraneStatus = params.get('membrane');
        if (membraneStatus === 'connected') {
            this.loadMembraneData();
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

    loadMembraneData(): void {
        this.membraneLoading = true;
        this.membraneError = null;
        this.membraneService.getIntegrations().subscribe({
            next: (integrationsRes) => {
                this.membraneIntegrations = integrationsRes.items;
                this.membraneService.getConnections().subscribe({
                    next: (connectionsRes) => {
                        this.membraneConnections = connectionsRes.items;
                        this.membraneLoading = false;
                    },
                    error: (err) => {
                        this.membraneLoading = false;
                        if (err?.status !== 502) {
                            this.membraneError = 'Failed to load integration connections.';
                        }
                    },
                });
            },
            error: (err) => {
                this.membraneLoading = false;
                if (err?.status === 503) {
                    this.membraneError = 'Membrane integration is not configured on this instance.';
                }
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

    connectMembrane(integrationKey: string): void {
        this.membraneService.openConnection(integrationKey);
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

    disconnectMembrane(connectionId: string): void {
        if (!confirm('Disconnect this integration? Your synced data will be preserved.')) {
            return;
        }
        // TODO: call membrane disconnect API when available
        this.membraneConnections = this.membraneConnections.filter(c => c.id !== connectionId);
    }

    forceSync(): void {
        this.ms365Syncing = true;
        this.ms365Error = null;
        this.ms365Service.triggerSync().subscribe({
            next: () => {
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

    onSearch(query: string): void {
        this.searchQuery = query;
    }

    // ── Helpers ─────────────────────────────────────────────────

    private _iconForIntegration(key: string): string {
        const map: Record<string, string> = {
            'microsoft-outlook': 'fa-brands fa-microsoft',
            'hubspot': 'fa-brands fa-hubspot',
            'salesforce': 'fa-brands fa-salesforce',
            'slack': 'fa-brands fa-slack',
            'google-workspace': 'fa-brands fa-google',
            'mailchimp': 'fa-brands fa-mailchimp',
            'stripe': 'fa-brands fa-stripe',
            'github': 'fa-brands fa-github',
        };
        return map[key.toLowerCase()] || 'fa-solid fa-plug';
    }

    private _colorClassForIntegration(key: string): string {
        const map: Record<string, string> = {
            'microsoft-outlook': 'integration-card__icon--ms',
            'hubspot': 'integration-card__icon--orange',
            'salesforce': 'integration-card__icon--sf',
            'slack': 'integration-card__icon--purple',
            'google-workspace': 'integration-card__icon--blue',
            'mailchimp': 'integration-card__icon--mc',
            'stripe': 'integration-card__icon--indigo',
            'github': 'integration-card__icon--github',
        };
        return map[key.toLowerCase()] || 'integration-card__icon--gray';
    }

    private _defaultDescription(key: string): string {
        const map: Record<string, string> = {
            'microsoft-outlook': 'Sync emails and calendar with Microsoft Outlook',
            'hubspot': 'Sync contacts and deals with HubSpot CRM',
            'salesforce': 'Bi-directional sync with Salesforce CRM',
            'slack': 'Get notifications and send messages to Slack',
        };
        return map[key.toLowerCase()] || 'Connect this integration to your workspace';
    }
}
