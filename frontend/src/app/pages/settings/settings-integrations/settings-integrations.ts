import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MS365Service } from '../../../shared/services/ms365.service';
import { MembraneService } from '../../../shared/services/membrane.service';
import { IntegrationSettingsService } from '../../../shared/services/integration-settings.service';
import { AuthService } from '../../../shared/services/auth.service';
import { MS365Connection } from '../../../shared/models/ms365.model';
import { MembraneConnection, MembraneIntegration, MembraneConfig } from '../../../shared/models/membrane.model';
import { IntegrationSetting } from '../../../shared/models/integration-setting.model';

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
    imports: [CommonModule, RouterLink, FormsModule],
    templateUrl: './settings-integrations.html',
    styleUrls: ['../settings-shared.css'],
})
export class SettingsIntegrationsComponent implements OnInit {
    private ms365Service = inject(MS365Service);
    private membraneService = inject(MembraneService);
    private integrationSettingsService = inject(IntegrationSettingsService);
    private authService = inject(AuthService);

    // Legacy MS365 state (deprecated — kept during transition for existing connections)
    ms365Connection: MS365Connection | null = null;
    ms365Loading = false;
    ms365Syncing = false;
    ms365Error: string | null = null;

    /** Key used consistently for the Outlook integration across legacy and Membrane. */
    readonly OUTLOOK_KEY = 'microsoft-outlook';

    // Membrane state
    membraneConnections: MembraneConnection[] = [];
    membraneIntegrations: MembraneIntegration[] = [];
    membraneLoading = false;
    membraneError: string | null = null;
    searchQuery = '';

    // Admin config
    integrationSettings: IntegrationSetting[] = [];
    isAdmin = false;

    // Membrane platform config modal
    showMembraneConfigModal = false;
    membraneConfigured = false;
    /** True when the server confirmed a secret is already stored. Drives the
     *  masked placeholder so users can see "there's one, I just don't display
     *  it for security" instead of an empty field (which reads as "unset"). */
    membraneSecretConfigured = false;
    /** Local flag: user clicked "Change secret" and is now editing freely. */
    membraneEditingSecret = false;
    membraneConfigForm: MembraneConfig = {
        workspace_key: '',
        workspace_secret: '',
        api_url: 'https://api.getmembrane.com',
    };
    membraneConfigSaving = false;
    membraneConfigError: string | null = null;
    membraneConfigSuccess: string | null = null;

    get connectedIntegrations(): IntegrationViewModel[] {
        const connected: IntegrationViewModel[] = [];
        const hasMembraneOutlook = this.membraneConnections.some(
            c => !c.disconnected && c.integration_key === this.OUTLOOK_KEY,
        );
        // Legacy MS365 (during transition) — only shown if no Membrane Outlook yet
        if (this.ms365IsConnected && !hasMembraneOutlook) {
            connected.push({
                key: this.OUTLOOK_KEY,
                name: 'Microsoft Outlook',
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

    /** True when the Membrane catalog already lists Microsoft-Outlook. */
    get _hasOutlookInMembraneCatalog(): boolean {
        return this.membraneIntegrations.some(i => i.key === this.OUTLOOK_KEY);
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
        const availableKeys = new Set(available.map(a => a.key));
        for (const h of hardcoded) {
            if (!connectedKeys.has(h.key) && !availableKeys.has(h.key)) {
                available.push(h);
            }
        }

        // Legacy MS365 available (only if no Membrane connection AND not in Membrane catalog already)
        if (!this.ms365IsConnected && !this._hasOutlookInMembraneCatalog) {
            available.unshift({
                key: this.OUTLOOK_KEY,
                name: 'Microsoft Outlook',
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
        this.authService.user$.subscribe((user) => {
            this.isAdmin = user?.role === 'admin' || user?.is_super_admin === true;
            if (this.isAdmin) {
                this.loadIntegrationSettings();
            }
        });

        this.loadMs365Status();
        this.loadMembraneData();
        // Load config status on mount so the top banner accurately shows
        // "Configured" vs "Not configured" without requiring the user to
        // open the modal first.
        this.loadMembraneConfig();

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

    // ── Admin Settings ──────────────────────────────────────────────

    loadIntegrationSettings(): void {
        this.integrationSettingsService.list().subscribe({
            next: (res) => {
                this.integrationSettings = res.items;
            },
            error: (err) => {
                console.error('Failed to load integration settings', err);
            },
        });
    }

    getSettingFor(integrationKey: string): IntegrationSetting | undefined {
        return this.integrationSettings.find(s => s.integration_key === integrationKey);
    }

    getScopeFor(integrationKey: string): string {
        return this.getSettingFor(integrationKey)?.scope_mode ?? 'per-user';
    }

    setScope(integrationKey: string, scope: string): void {
        const existing = this.getSettingFor(integrationKey);
        const payload = { integration_key: integrationKey, scope_mode: scope, is_enabled: true };
        if (existing) {
            this.integrationSettingsService.update(integrationKey, { scope_mode: scope }).subscribe({
                next: () => this.loadIntegrationSettings(),
                error: (err) => console.error('Failed to update scope', err),
            });
        } else {
            this.integrationSettingsService.upsert(payload).subscribe({
                next: () => this.loadIntegrationSettings(),
                error: (err) => console.error('Failed to create setting', err),
            });
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

    disconnectMembrane(connection: MembraneConnection): void {
        if (!confirm('Disconnect this integration? Your synced data will be preserved.')) {
            return;
        }
        this.membraneLoading = true;
        this.membraneService.disconnect(connection.id, connection.integration_key).subscribe({
            next: () => {
                this.membraneLoading = false;
                this.membraneConnections = this.membraneConnections.filter(c => c.id !== connection.id);
            },
            error: (err) => {
                this.membraneLoading = false;
                console.error('Failed to disconnect Membrane integration', err);
                alert('Failed to disconnect. Please try again.');
            },
        });
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

    _iconForIntegration(key: string): string {
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

    _colorClassForIntegration(key: string): string {
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

    _defaultDescription(key: string): string {
        const map: Record<string, string> = {
            'microsoft-outlook': 'Sync emails and calendar with Microsoft Outlook',
            'hubspot': 'Sync contacts and deals with HubSpot CRM',
            'salesforce': 'Bi-directional sync with Salesforce CRM',
            'slack': 'Get notifications and send messages to Slack',
        };
        return map[key.toLowerCase()] || 'Connect this integration to your workspace';
    }

    // ── Membrane Platform Config ─────────────────────────────────

    openMembraneConfig(): void {
        this.membraneConfigError = null;
        this.membraneConfigSuccess = null;
        this.membraneConfigSaving = false;
        this.membraneEditingSecret = false;
        this.loadMembraneConfig();
        this.showMembraneConfigModal = true;
    }

    closeMembraneConfig(): void {
        this.showMembraneConfigModal = false;
        this.membraneEditingSecret = false;
    }

    /** User clicks "Change secret" — unlocks the secret input for editing. */
    startEditingSecret(): void {
        this.membraneEditingSecret = true;
        this.membraneConfigForm.workspace_secret = '';
    }

    /** User clicks "Keep existing secret" — locks the input back. */
    cancelEditingSecret(): void {
        this.membraneEditingSecret = false;
        this.membraneConfigForm.workspace_secret = '';
    }

    loadMembraneConfig(): void {
        this.membraneService.getConfig().subscribe({
            next: (res) => {
                this.membraneConfigured = res.configured;
                this.membraneSecretConfigured = res.secret_configured;
                this.membraneConfigForm.workspace_key = res.workspace_key;
                this.membraneConfigForm.api_url = res.api_url;
                this.membraneConfigForm.workspace_secret = '';
                // If no secret exists yet, open the input in edit mode so the
                // user can type something; otherwise show it as locked/masked.
                this.membraneEditingSecret = !res.secret_configured;
            },
            error: (err) => {
                console.error('Failed to load Membrane config', err);
            },
        });
    }

    saveMembraneConfig(): void {
        this.membraneConfigError = null;
        this.membraneConfigSuccess = null;

        // Build a partial payload — omit the secret when the user isn't actively
        // editing it. This prevents the common "I opened the modal, saved, and
        // my secret got wiped because the field was empty" footgun.
        const payload: MembraneConfig = {
            workspace_key: this.membraneConfigForm.workspace_key,
            api_url: this.membraneConfigForm.api_url,
        };
        if (this.membraneEditingSecret && this.membraneConfigForm.workspace_secret) {
            payload.workspace_secret = this.membraneConfigForm.workspace_secret;
        }

        this.membraneConfigSaving = true;
        this.membraneService.updateConfig(payload).subscribe({
            next: (res) => {
                this.membraneConfigSaving = false;
                this.membraneConfigured = res.configured;
                this.membraneSecretConfigured = res.secret_configured;
                this.membraneEditingSecret = false;
                this.membraneConfigForm.workspace_secret = '';
                this.membraneConfigSuccess = res.message || 'Configuration saved successfully';
                this.loadMembraneData();
            },
            error: (err) => {
                this.membraneConfigSaving = false;
                this.membraneConfigError = err?.error?.detail || 'Failed to save configuration. Check your credentials.';
            },
        });
    }
}
