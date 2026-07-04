import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MS365Service } from '../../../shared/services/ms365.service';
import { MembraneService } from '../../../shared/services/membrane.service';
import { AuthService } from '../../../shared/services/auth.service';
import { MS365Connection } from '../../../shared/models/ms365.model';
import { MembraneConnection, MembraneIntegration, MembraneConfig, MembranePageInfo, MembraneTool } from '../../../shared/models/membrane.model';
import { ToolGovernancePolicy, UserToolAccessResponse } from '../../../shared/models/tool-governance.model';
import { ToolGovernanceService } from '../../../shared/services/tool-governance.service';

type IntegrationViewModel = {
    key: string;
    name: string;
    iconClass: string;
    iconColorClass: string;
    description: string;
    accountLabel?: string;
    iconUrl?: string;
    connection?: MembraneConnection;
    isLegacyMs365?: boolean;
    isManaged?: boolean;
    statusLabel?: string;
};

type ToolDetailField = {
    label: string;
    value: string;
    code?: boolean;
};

type ToolDetailModal = {
    integration: IntegrationViewModel;
    tool: MembraneTool;
    fields: ToolDetailField[];
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
    private authService = inject(AuthService);
    private toolGovernance = inject(ToolGovernanceService);

    // Legacy MS365 state (deprecated — kept during transition for existing connections)
    ms365Connection: MS365Connection | null = null;
    ms365Loading = false;
    ms365Syncing = false;
    ms365Error: string | null = null;

    /** Key used consistently for the Outlook integration across legacy and Pipedream. */
    readonly OUTLOOK_KEY = 'microsoft-outlook';

    // Pipedream state
    membraneConnections: MembraneConnection[] = [];
    membraneIntegrations: MembraneIntegration[] = [];
    membranePageInfo: MembranePageInfo | null = null;
    membraneLoading = false;
    membraneLoadingMore = false;
    membraneError: string | null = null;
    searchQuery = '';
    private searchTimer: ReturnType<typeof setTimeout> | null = null;
    private readonly catalogLimit = 100;

    toolsByIntegration: Record<string, MembraneTool[]> = {};
    toolPageInfoByIntegration: Record<string, MembranePageInfo | undefined> = {};
    toolLoadingByIntegration: Record<string, boolean> = {};
    toolErrorByIntegration: Record<string, string | null> = {};
    expandedToolKeys: Record<string, boolean> = {};
    brokenLogoKeys: Record<string, boolean> = {};
    toolAccess: UserToolAccessResponse | null = null;
    toolGovernanceLoading = false;
    toolGovernanceError: string | null = null;
    selectedToolDetails: ToolDetailModal | null = null;

    isAdmin = false;

    // Pipedream platform config modal
    showMembraneConfigModal = false;
    membraneConfigured = false;
    /** True when the server confirmed a secret is already stored. Drives the
     *  masked placeholder so users can see "there's one, I just don't display
     *  it for security" instead of an empty field (which reads as "unset"). */
    membraneSecretConfigured = false;
    /** Local flag: user clicked "Change secret" and is now editing freely. */
    membraneEditingSecret = false;
    membraneConfigForm: MembraneConfig = {
        client_id: '',
        client_secret: '',
        project_id: '',
        environment: 'development',
        api_url: 'https://api.pipedream.com/v1',
    };
    membraneConfigSaving = false;
    membraneConfigError: string | null = null;
    membraneConfigSuccess: string | null = null;

    get connectedIntegrations(): IntegrationViewModel[] {
        const connected: IntegrationViewModel[] = [];
        const hasMembraneOutlook = this.membraneConnections.some(
            c => !c.disconnected && this._connectionKey(c) === this.OUTLOOK_KEY,
        );
        // Legacy MS365 (during transition) — only shown if no Pipedream Outlook yet
        if (this.ms365IsConnected && !hasMembraneOutlook) {
            connected.push({
                key: this.OUTLOOK_KEY,
                name: 'Microsoft Outlook',
                iconClass: 'fa-brands fa-microsoft',
                iconColorClass: 'integration-card__icon--ms',
                description: this.ms365Connection?.ms_email || 'Outlook, Calendar',
                accountLabel: this.ms365Connection?.ms_email || undefined,
                isLegacyMs365: true,
            });
        }
        // Pipedream connections
        for (const conn of this.membraneConnections) {
            if (conn.disconnected) continue;
            const key = this._connectionKey(conn);
            const integration = this.membraneIntegrations.find(i => i.key === key || i.id === conn.integration_id);
            const accountLabel = this._accountLabelForConnection(conn, key);
            connected.push({
                key,
                name: integration?.name || this._displayNameForIntegration(key),
                iconClass: this._iconForIntegration(key),
                iconColorClass: this._colorClassForIntegration(key),
                description: accountLabel,
                accountLabel,
                iconUrl: integration?.iconUrl || integration?.logo_uri,
                connection: conn,
            });
        }
        return connected;
    }

    /** True when the Pipedream catalog already lists Microsoft-Outlook. */
    get _hasOutlookInMembraneCatalog(): boolean {
        return this.membraneIntegrations.some(i => i.key === this.OUTLOOK_KEY);
    }

    get availableIntegrations(): IntegrationViewModel[] {
        const connectedKeys = new Set(this.connectedIntegrations.map(i => i.key));
        const available: IntegrationViewModel[] = [];

        // Pipedream integrations not yet connected
        for (const integration of this.membraneIntegrations) {
            if (!connectedKeys.has(integration.key)) {
                available.push({
                    key: integration.key,
                    name: integration.name,
                    iconClass: this._iconForIntegration(integration.key),
                    iconColorClass: this._colorClassForIntegration(integration.key),
                    description: integration.description || this._defaultDescription(integration.key),
                    iconUrl: integration.iconUrl || integration.logo_uri,
                });
            }
        }

        // Filter by search
        if (this.searchQuery.trim()) {
            const q = this.searchQuery.toLowerCase();
            return available.filter(i => i.name.toLowerCase().includes(q) || i.description.toLowerCase().includes(q));
        }
        return available;
    }

    get managedIntegrations(): IntegrationViewModel[] {
        const cards = this._buildManagedIntegrationCards(this._visibleToolPolicies());
        if (this.searchQuery.trim()) {
            const q = this.searchQuery.toLowerCase();
            return cards.filter(card =>
                card.name.toLowerCase().includes(q)
                || card.description.toLowerCase().includes(q)
                || this.toolsFor(card.key).some(tool => `${tool.name} ${tool.description || ''}`.toLowerCase().includes(q)),
            );
        }
        return cards;
    }

    ngOnInit(): void {
        this.authService.user$.subscribe((user) => {
            this.isAdmin = user?.role === 'admin' || user?.is_super_admin === true;
        });

        this.loadMs365Status();
        this.loadMembraneData();
        this.loadToolGovernanceAccess();
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

        // Pipedream callback
        const membraneStatus = params.get('pipedream') || params.get('membrane');
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

    loadMembraneData(reset = true): void {
        const query = this.searchQuery.trim() || undefined;
        const after = reset ? undefined : this.membranePageInfo?.end_cursor;
        if (!reset && !after) {
            return;
        }

        this.membraneLoading = reset;
        this.membraneLoadingMore = !reset;
        this.membraneError = null;
        this.membraneService.getIntegrations(query, after, this.catalogLimit).subscribe({
            next: (integrationsRes) => {
                this.membraneIntegrations = reset
                    ? integrationsRes.items
                    : this._mergeIntegrations(this.membraneIntegrations, integrationsRes.items);
                this.membranePageInfo = integrationsRes.page_info || null;

                if (!reset) {
                    this.membraneLoadingMore = false;
                    return;
                }

                this.loadMembraneConnections();
            },
            error: (err) => {
                this.membraneLoading = false;
                this.membraneLoadingMore = false;
                if (err?.status === 503) {
                    this.membraneError = 'Pipedream integration is not configured on this instance.';
                } else {
                    this.membraneError = 'Failed to load integration catalog.';
                }
            },
        });
    }

    loadMembraneConnections(): void {
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
    }

    loadToolGovernanceAccess(): void {
        this.toolGovernanceLoading = true;
        this.toolGovernanceError = null;
        this.toolGovernance.getMyAccess().subscribe({
            next: (access) => {
                this.toolAccess = access;
                this._syncManagedIntegrationTools(this._visibleToolPolicies(access));
                this.toolGovernanceLoading = false;
            },
            error: () => {
                this.toolGovernanceLoading = false;
                this.toolGovernanceError = 'Failed to load Croo tools.';
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
                console.error('Failed to disconnect Pipedream integration', err);
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
        if (this.searchTimer) {
            clearTimeout(this.searchTimer);
        }
        this.searchTimer = setTimeout(() => this.loadMembraneData(true), 250);
    }

    loadMoreIntegrations(): void {
        this.loadMembraneData(false);
    }

    get hasMoreIntegrations(): boolean {
        if (!this.membranePageInfo?.end_cursor) {
            return false;
        }
        const total = this.membranePageInfo.total_count;
        return total === undefined || this.membraneIntegrations.length < total;
    }

    toggleTools(integrationKey: string): void {
        this.expandedToolKeys[integrationKey] = !this.expandedToolKeys[integrationKey];
        if (this.expandedToolKeys[integrationKey] && !this.toolsByIntegration[integrationKey]) {
            this.loadIntegrationTools(integrationKey);
        }
    }

    loadIntegrationTools(integrationKey: string, after?: string): void {
        if (this.toolLoadingByIntegration[integrationKey]) {
            return;
        }

        this.toolLoadingByIntegration[integrationKey] = true;
        this.toolErrorByIntegration[integrationKey] = null;
        this.membraneService.getIntegrationTools(integrationKey, undefined, after).subscribe({
            next: (res) => {
                this.toolsByIntegration[integrationKey] = after
                    ? [...(this.toolsByIntegration[integrationKey] || []), ...res.items]
                    : res.items;
                this.toolPageInfoByIntegration[integrationKey] = res.page_info;
                this.toolLoadingByIntegration[integrationKey] = false;
            },
            error: () => {
                this.toolLoadingByIntegration[integrationKey] = false;
                this.toolErrorByIntegration[integrationKey] = 'Failed to load tools.';
            },
        });
    }

    loadMoreTools(integrationKey: string): void {
        const cursor = this.toolPageInfoByIntegration[integrationKey]?.end_cursor;
        if (cursor) {
            this.loadIntegrationTools(integrationKey, cursor);
        }
    }

    isToolsExpanded(integrationKey: string): boolean {
        return !!this.expandedToolKeys[integrationKey];
    }

    toolsFor(integrationKey: string): MembraneTool[] {
        return this.toolsByIntegration[integrationKey] || [];
    }

    toolsTotalFor(integrationKey: string): number {
        return this.toolPageInfoByIntegration[integrationKey]?.total_count ?? this.toolsFor(integrationKey).length;
    }

    hasMoreTools(integrationKey: string): boolean {
        const cursor = this.toolPageInfoByIntegration[integrationKey]?.end_cursor;
        const total = this.toolPageInfoByIntegration[integrationKey]?.total_count;
        return !!cursor && (total === undefined || this.toolsFor(integrationKey).length < total);
    }

    openToolDetails(integration: IntegrationViewModel, tool: MembraneTool): void {
        this.selectedToolDetails = {
            integration,
            tool,
            fields: this._toolDetailFields(tool),
        };
    }

    closeToolDetails(): void {
        this.selectedToolDetails = null;
    }

    logoFor(integration: { key: string; iconUrl?: string; logo_uri?: string }): string | undefined {
        return this.brokenLogoKeys[integration.key] ? undefined : integration.iconUrl || integration.logo_uri;
    }

    onIntegrationLogoError(integrationKey: string): void {
        this.brokenLogoKeys[integrationKey] = true;
    }

    // ── Helpers ─────────────────────────────────────────────────

    private _mergeIntegrations(existing: MembraneIntegration[], incoming: MembraneIntegration[]): MembraneIntegration[] {
        const seen = new Set(existing.map(integration => integration.key));
        return [
            ...existing,
            ...incoming.filter(integration => {
                if (seen.has(integration.key)) {
                    return false;
                }
                seen.add(integration.key);
                return true;
            }),
        ];
    }

    private _visibleToolPolicies(access = this.toolAccess): ToolGovernancePolicy[] {
        return access?.policies?.length ? access.policies : access?.allowed_tools || [];
    }

    private _buildManagedIntegrationCards(policies: ToolGovernancePolicy[]): IntegrationViewModel[] {
        const byKey = new Map<string, { card: IntegrationViewModel; order: number }>();
        for (const policy of policies) {
            const definition = this._managedIntegrationDefinition(policy);
            const existing = byKey.get(definition.key);
            if (existing) {
                existing.card.statusLabel = existing.card.statusLabel === 'Enabled' || policy.enabled ? 'Enabled' : 'Disabled';
                continue;
            }
            byKey.set(definition.key, {
                card: {
                    ...definition,
                    isManaged: true,
                    statusLabel: policy.enabled ? 'Enabled' : 'Disabled',
                },
                order: this._managedIntegrationOrder(definition.key),
            });
        }
        return Array.from(byKey.values())
            .sort((a, b) => a.order - b.order || a.card.name.localeCompare(b.card.name))
            .map(item => item.card);
    }

    private _syncManagedIntegrationTools(policies: ToolGovernancePolicy[]): void {
        const grouped: Record<string, MembraneTool[]> = {};
        for (const policy of policies) {
            const definition = this._managedIntegrationDefinition(policy);
            grouped[definition.key] = grouped[definition.key] || [];
            if (grouped[definition.key].some(tool => tool.key === policy.id)) {
                continue;
            }
            grouped[definition.key].push({
                key: policy.id,
                name: policy.display_name || policy.id,
                description: this._managedToolDescription(policy),
                component_type: policy.provider,
                annotations: {
                    enabled: policy.enabled ? 'enabled' : 'disabled',
                    family: policy.family,
                    capability: policy.capability,
                    integration: policy.integration_key,
                    tool_key: policy.tool_key,
                    risk: policy.risk,
                    source: policy.source,
                    sync_mode: policy.sync_mode,
                    notes: policy.notes,
                    ...(policy.data_mapping || {}),
                },
            });
        }
        for (const [key, tools] of Object.entries(grouped)) {
            this.toolsByIntegration[key] = tools.sort((a, b) => a.name.localeCompare(b.name));
            this.toolPageInfoByIntegration[key] = {
                count: tools.length,
                total_count: tools.length,
            };
        }
    }

    private _managedIntegrationDefinition(policy: ToolGovernancePolicy): IntegrationViewModel {
        const family = this._normalizeIntegrationKey(policy.family || policy.integration_key || policy.provider || 'croo-agentic');
        const capability = this._normalizeIntegrationKey(policy.capability || policy.id || '');
        if (family === 'skyswitch' && capability.startsWith('pbx-')) {
            return {
                key: 'croo-netsapiens-pbx',
                name: 'NetSapiens PBX',
                iconClass: 'fa-solid fa-phone-volume',
                iconColorClass: 'integration-card__icon--blue',
                description: 'PBX, subscribers, queues, IVR and voice tooling from Croo agentic.',
            };
        }
        if (family === 'skyswitch') {
            return {
                key: 'croo-skyswitch-telco',
                name: 'SkySwitch Telco',
                iconClass: 'fa-solid fa-tower-cell',
                iconColorClass: 'integration-card__icon--purple',
                description: 'Telco status, API, DIDs and routing through Croo agentic.',
            };
        }

        const definitions: Record<string, IntegrationViewModel> = {
            'runtime': {
                key: 'croo-agentic-runtime',
                name: 'Croo Agentic Runtime',
                iconClass: 'fa-solid fa-microchip',
                iconColorClass: 'integration-card__icon--gray',
                description: 'Runtime status, memory, and Bob control center tools.',
            },
            'memory': {
                key: 'croo-agentic-runtime',
                name: 'Croo Agentic Runtime',
                iconClass: 'fa-solid fa-microchip',
                iconColorClass: 'integration-card__icon--gray',
                description: 'Runtime status, memory, and Bob control center tools.',
            },
            'mcp': {
                key: 'croo-agentic-runtime',
                name: 'Croo Agentic Runtime',
                iconClass: 'fa-solid fa-microchip',
                iconColorClass: 'integration-card__icon--gray',
                description: 'Runtime status, memory, and Bob control center tools.',
            },
            'assistant-memory': {
                key: 'croo-agentic-memory',
                name: 'Croo Agentic Memory',
                iconClass: 'fa-solid fa-brain',
                iconColorClass: 'integration-card__icon--purple',
                description: 'Private and organization memory capabilities.',
            },
            'support-memory': {
                key: 'croo-support-memory',
                name: 'Support Memory',
                iconClass: 'fa-solid fa-book-open',
                iconColorClass: 'integration-card__icon--blue',
                description: 'Support playbooks, search, and training review tools.',
            },
            'bob-control-center': {
                key: 'croo-bob-control-center',
                name: 'Bob Control Center',
                iconClass: 'fa-solid fa-sliders',
                iconColorClass: 'integration-card__icon--gray',
                description: 'Agent, skill, tool, profile, and permission catalogs.',
            },
            'croo-connect': {
                key: 'croo-connect',
                name: 'Croo Connect',
                iconClass: 'fa-solid fa-link',
                iconColorClass: 'integration-card__icon--blue',
                description: 'Croo account connection and supported app routing.',
            },
            'factory': {
                key: 'croo-factory',
                name: 'Factory',
                iconClass: 'fa-solid fa-diagram-project',
                iconColorClass: 'integration-card__icon--gray',
                description: 'Projects, requests, queues, validation, and PO learning.',
            },
            'gitlab-code': {
                key: 'croo-gitlab-code',
                name: 'GitLab Code',
                iconClass: 'fa-brands fa-gitlab',
                iconColorClass: 'integration-card__icon--orange',
                description: 'Projects, branches, tree, files, and code search.',
            },
            'browser': {
                key: 'croo-browser',
                name: 'Browser',
                iconClass: 'fa-solid fa-window-restore',
                iconColorClass: 'integration-card__icon--blue',
                description: 'Chrome/browser state, screenshots, and controlled interactions.',
            },
            'web-research': {
                key: 'croo-web-research',
                name: 'Web Research',
                iconClass: 'fa-solid fa-magnifying-glass',
                iconColorClass: 'integration-card__icon--gray',
                description: 'Current search, sources, citations, data and calculations.',
            },
            'zoho': {
                key: 'croo-zoho',
                name: 'Zoho',
                iconClass: 'fa-solid fa-headset',
                iconColorClass: 'integration-card__icon--orange',
                description: 'Zoho Desk, Billing, Books, CRM and campaign tools.',
            },
            'mail-calendar': {
                key: 'croo-mail-calendar',
                name: 'Mail & Calendar',
                iconClass: 'fa-solid fa-envelope-open-text',
                iconColorClass: 'integration-card__icon--gmail',
                description: 'Email and calendar tools governed by Bob.',
            },
            'slack': {
                key: 'croo-slack-tools',
                name: 'Slack Tools',
                iconClass: 'fa-brands fa-slack',
                iconColorClass: 'integration-card__icon--purple',
                description: 'Slack channels, messages, drafts and managed actions.',
            },
            'teams': {
                key: 'croo-teams-tools',
                name: 'Teams Tools',
                iconClass: 'fa-brands fa-microsoft',
                iconColorClass: 'integration-card__icon--ms',
                description: 'Teams channels, chats, messages and management tools.',
            },
            'workspace-files': {
                key: 'croo-workspace-files',
                name: 'Workspace Files',
                iconClass: 'fa-solid fa-folder-open',
                iconColorClass: 'integration-card__icon--blue',
                description: 'Drive, OneDrive, Sheets and local file tools.',
            },
            'pipedream-supabase': {
                key: 'croo-pipedream-supabase',
                name: 'Supabase',
                iconClass: 'fa-solid fa-database',
                iconColorClass: 'integration-card__icon--sf',
                description: 'Supabase count, select, write/RPC and options tools.',
            },
        };
        return definitions[family] || {
            key: `croo-${family || 'agentic'}`,
            name: this._displayNameForIntegration(family || 'croo-agentic'),
            iconClass: 'fa-solid fa-plug',
            iconColorClass: 'integration-card__icon--gray',
            description: 'Croo agentic tools available to Bob.',
        };
    }

    private _managedToolDescription(policy: ToolGovernancePolicy): string {
        const parts = [
            policy.enabled ? 'enabled' : 'disabled',
            policy.provider,
            policy.family || policy.integration_key,
            policy.capability,
            policy.risk,
        ].filter(Boolean);
        return parts.join(' · ');
    }

    private _toolDetailFields(tool: MembraneTool): ToolDetailField[] {
        const annotations = tool.annotations || {};
        const knownAnnotationKeys = new Set([
            'capability',
            'enabled',
            'family',
            'integration',
            'api_action',
            'api_base_hint',
            'api_object',
            'api_scope',
            'api_surface',
            'doc_operation',
            'doc_section',
            'doc_url',
            'endpoint',
            'guardrail',
            'http_method',
            'notes',
            'portal_url',
            'provider',
            'read_only_test',
            'risk',
            'source',
            'sync_mode',
            'tool_key',
        ]);
        const fields: ToolDetailField[] = [];
        const addField = (label: string, value: unknown, code = false): void => {
            const formatted = this._formatToolMetadata(value);
            if (!formatted) return;
            if (fields.some(field => field.label === label && field.value === formatted)) return;
            fields.push({ label, value: formatted, code });
        };

        addField('Tool ID', tool.key, true);
        addField('Provider', tool.component_type || annotations['provider']);
        addField('Enabled', annotations['enabled']);
        addField('Family', annotations['family']);
        addField('Integration', annotations['integration']);
        addField('Capability', annotations['capability']);
        addField('Action key', annotations['tool_key'], true);
        addField('Risk', annotations['risk']);
        addField('Doc section', annotations['doc_section']);
        addField('Doc operation', annotations['doc_operation']);
        addField('Doc URL', annotations['doc_url']);
        addField('API surface', annotations['api_surface']);
        addField('API scope', annotations['api_scope']);
        addField('Endpoint', annotations['endpoint'], true);
        addField('HTTP method', annotations['http_method']);
        addField('Object', annotations['api_object'], true);
        addField('Action', annotations['api_action'], true);
        addField('Portal', annotations['portal_url']);
        addField('API base', annotations['api_base_hint'], true);
        addField('Guardrail', annotations['guardrail']);
        addField('Source', annotations['source']);
        addField('Sync mode', annotations['sync_mode']);
        addField('Read-only test', annotations['read_only_test']);
        addField('Notes', annotations['notes']);
        addField('Version', tool.version);
        if (typeof tool.configurable_props_count === 'number') {
            addField('Configurable inputs', tool.configurable_props_count);
        }

        for (const [key, value] of Object.entries(annotations)) {
            if (!knownAnnotationKeys.has(key)) {
                addField(this._humanizeMetadataKey(key), value);
            }
        }

        return fields;
    }

    private _formatToolMetadata(value: unknown): string {
        if (value === null || value === undefined || value === '') {
            return '';
        }
        if (Array.isArray(value)) {
            return value.length > 0 ? value.map(item => this._formatToolMetadata(item)).filter(Boolean).join(', ') : '';
        }
        if (typeof value === 'object') {
            return JSON.stringify(value);
        }
        return String(value);
    }

    private _humanizeMetadataKey(key: string): string {
        const normalized = key.replace(/[_-]+/g, ' ');
        return normalized.charAt(0).toUpperCase() + normalized.slice(1);
    }

    private _managedIntegrationOrder(key: string): number {
        const order: Record<string, number> = {
            'croo-skyswitch-telco': 10,
            'croo-netsapiens-pbx': 11,
            'croo-agentic-runtime': 20,
            'croo-bob-control-center': 21,
            'croo-agentic-memory': 22,
            'croo-support-memory': 23,
            'croo-factory': 30,
            'croo-gitlab-code': 31,
            'croo-zoho': 32,
        };
        return order[key] ?? 100;
    }

    _iconForIntegration(key: string): string {
        const map: Record<string, string> = {
            'gmail': 'fa-solid fa-envelope',
            'google-gmail': 'fa-solid fa-envelope',
            'google-calendar': 'fa-solid fa-calendar-days',
            'microsoft-outlook-email': 'fa-brands fa-microsoft',
            'microsoft-outlook-calendar': 'fa-solid fa-calendar-days',
            'microsoft-outlook': 'fa-brands fa-microsoft',
            'hubspot': 'fa-brands fa-hubspot',
            'salesforce': 'fa-brands fa-salesforce',
            'slack': 'fa-brands fa-slack',
            'slack-v2': 'fa-brands fa-slack',
            'google-workspace': 'fa-brands fa-google',
            'google': 'fa-brands fa-google',
            'mailchimp': 'fa-brands fa-mailchimp',
            'stripe': 'fa-brands fa-stripe',
            'github': 'fa-brands fa-github',
        };
        return map[this._normalizeIntegrationKey(key)] || 'fa-solid fa-plug';
    }

    _colorClassForIntegration(key: string): string {
        const map: Record<string, string> = {
            'gmail': 'integration-card__icon--gmail',
            'google-gmail': 'integration-card__icon--gmail',
            'google-calendar': 'integration-card__icon--blue',
            'microsoft-outlook-email': 'integration-card__icon--ms',
            'microsoft-outlook-calendar': 'integration-card__icon--ms',
            'microsoft-outlook': 'integration-card__icon--ms',
            'hubspot': 'integration-card__icon--orange',
            'salesforce': 'integration-card__icon--sf',
            'slack': 'integration-card__icon--purple',
            'slack-v2': 'integration-card__icon--purple',
            'google-workspace': 'integration-card__icon--blue',
            'google': 'integration-card__icon--blue',
            'mailchimp': 'integration-card__icon--mc',
            'stripe': 'integration-card__icon--indigo',
            'github': 'integration-card__icon--github',
        };
        return map[this._normalizeIntegrationKey(key)] || 'integration-card__icon--gray';
    }

    _defaultDescription(key: string): string {
        const map: Record<string, string> = {
            'gmail': 'Sync Gmail messages and labels',
            'google-gmail': 'Sync Gmail messages and labels',
            'google-calendar': 'Sync Google Calendar events',
            'microsoft-outlook-email': 'Sync Outlook email',
            'microsoft-outlook-calendar': 'Sync Outlook calendar',
            'microsoft-outlook': 'Sync emails and calendar with Microsoft Outlook',
            'hubspot': 'Sync contacts and deals with HubSpot CRM',
            'salesforce': 'Bi-directional sync with Salesforce CRM',
            'slack': 'Get notifications and send messages to Slack',
            'slack-v2': 'Get notifications and send messages to Slack',
        };
        return map[this._normalizeIntegrationKey(key)] || 'Connect this integration to your workspace';
    }

    // ── Pipedream Platform Config ─────────────────────────────────

    private _connectionKey(connection: MembraneConnection): string {
        const key = connection.integration_key || connection.app || connection.integration_id || '';
        return this._normalizeIntegrationKey(key);
    }

    private _normalizeIntegrationKey(key: string): string {
        return (key || '').replace(/^~connector\./, '').replace(/_/g, '-').toLowerCase();
    }

    private _displayNameForIntegration(key: string): string {
        const normalized = this._normalizeIntegrationKey(key);
        const map: Record<string, string> = {
            'gmail': 'Gmail',
            'google-gmail': 'Gmail',
            'google-calendar': 'Google Calendar',
            'google-workspace': 'Google Workspace',
            'google-drive': 'Google Drive',
            'microsoft-outlook': 'Microsoft Outlook',
            'microsoft-outlook-email': 'Microsoft Outlook Email',
            'microsoft-outlook-calendar': 'Microsoft Outlook Calendar',
            'hubspot': 'HubSpot',
            'salesforce': 'Salesforce',
            'slack': 'Slack',
            'slack-v2': 'Slack',
            'mailchimp': 'Mailchimp',
            'stripe': 'Stripe',
            'github': 'GitHub',
        };
        if (map[normalized]) {
            return map[normalized];
        }
        return normalized
            .split('-')
            .filter(Boolean)
            .map(part => part.length <= 3 ? part.toUpperCase() : part.charAt(0).toUpperCase() + part.slice(1))
            .join(' ') || 'Integration';
    }

    private _accountLabelForConnection(connection: MembraneConnection, key: string): string {
        const displayName = this._displayNameForIntegration(key);
        const label = connection.name || connection.integration_key || connection.app || displayName;
        return label === displayName ? 'Connected account' : label;
    }

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
        this.membraneConfigForm.client_secret = '';
    }

    /** User clicks "Keep existing secret" — locks the input back. */
    cancelEditingSecret(): void {
        this.membraneEditingSecret = false;
        this.membraneConfigForm.client_secret = '';
    }

    loadMembraneConfig(): void {
        this.membraneService.getConfig().subscribe({
            next: (res) => {
                this.membraneConfigured = res.configured;
                this.membraneSecretConfigured = res.secret_configured;
                this.membraneConfigForm.client_id = res.client_id;
                this.membraneConfigForm.project_id = res.project_id;
                this.membraneConfigForm.environment = res.environment;
                this.membraneConfigForm.api_url = res.api_url;
                this.membraneConfigForm.client_secret = '';
                // If no secret exists yet, open the input in edit mode so the
                // user can type something; otherwise show it as locked/masked.
                this.membraneEditingSecret = !res.secret_configured;
            },
            error: (err) => {
                console.error('Failed to load Pipedream config', err);
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
            client_id: this.membraneConfigForm.client_id,
            project_id: this.membraneConfigForm.project_id,
            environment: this.membraneConfigForm.environment,
            api_url: this.membraneConfigForm.api_url,
        };
        if (this.membraneEditingSecret && this.membraneConfigForm.client_secret) {
            payload.client_secret = this.membraneConfigForm.client_secret;
        }

        this.membraneConfigSaving = true;
        this.membraneService.updateConfig(payload).subscribe({
            next: (res) => {
                this.membraneConfigSaving = false;
                this.membraneConfigured = res.configured;
                this.membraneSecretConfigured = res.secret_configured;
                this.membraneEditingSecret = false;
                this.membraneConfigForm.client_secret = '';
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
