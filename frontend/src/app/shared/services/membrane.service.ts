import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
    MembraneTokenRequest,
    MembraneTokenResponse,
    MembraneConnectionListResponse,
    MembraneIntegrationListResponse,
    MembraneActionRunRequest,
    MembraneActionRunResponse,
    MembraneConnectUrlResponse,
    MembraneConfig,
    MembraneConfigResponse,
    MembraneToolListResponse,
} from '../models/membrane.model';

const API_URL = `${environment.communicationApiUrl}`;

/** Angular service for Pipedream integration platform.
 *
 * This service proxies all Pipedream interactions through the Croo backend.
 * The backend creates short-lived Connect tokens scoped to the current user.
 */
@Injectable({ providedIn: 'root' })
export class MembraneService {
    private http = inject(HttpClient);

    // ── Token ─────────────────────────────────────────────────────

    /** Get a short-lived Pipedream Connect token for a given integration. */
    getToken(integrationKey: string): Observable<MembraneTokenResponse> {
        return this.http.post<MembraneTokenResponse>(
            `${API_URL}/pipedream/token`,
            { integration_key: integrationKey } as MembraneTokenRequest,
        );
    }

    // ── Connections ───────────────────────────────────────────────

    /** List Pipedream connections for the current scoped user/entity. */
    getConnections(integrationKey?: string): Observable<MembraneConnectionListResponse> {
        let url = `${API_URL}/pipedream/connections`;
        if (integrationKey) {
            url += `?integration_key=${encodeURIComponent(integrationKey)}`;
        }
        return this.http.get<MembraneConnectionListResponse>(url);
    }

    // ── Integrations Catalog ─────────────────────────────────────

    /** List available Pipedream apps. */
    getIntegrations(query?: string, after?: string, limit = 100, hasActions = true): Observable<MembraneIntegrationListResponse> {
        let params = new HttpParams()
            .set('limit', String(limit))
            .set('has_actions', String(hasActions));
        if (query) {
            params = params.set('q', query);
        }
        if (after) {
            params = params.set('after', after);
        }
        return this.http.get<MembraneIntegrationListResponse>(`${API_URL}/pipedream/integrations`, { params });
    }

    /** List Pipedream actions/tools exposed by a specific app. */
    getIntegrationTools(integrationKey: string, query?: string, after?: string, limit = 8): Observable<MembraneToolListResponse> {
        let params = new HttpParams()
            .set('limit', String(limit))
            .set('registry', 'public');
        if (query) {
            params = params.set('q', query);
        }
        if (after) {
            params = params.set('after', after);
        }
        return this.http.get<MembraneToolListResponse>(
            `${API_URL}/pipedream/integrations/${encodeURIComponent(integrationKey)}/tools`,
            { params },
        );
    }

    // ── Actions ───────────────────────────────────────────────────

    /** Run a Pipedream action (e.g. send-email, create-deal). */
    runAction(actionKey: string, request: MembraneActionRunRequest): Observable<MembraneActionRunResponse> {
        return this.http.post<MembraneActionRunResponse>(
            `${API_URL}/pipedream/actions/${actionKey}/run`,
            request,
        );
    }

    // ── Hosted Connection URL ─────────────────────────────────────

    /** Get a hosted Pipedream Connect Link URL to redirect the user to.
     *  This is the simplest flow for Angular (no React SDK needed). */
    getConnectUrl(integrationKey: string, redirectUri?: string): Observable<MembraneConnectUrlResponse> {
        let url = `${API_URL}/pipedream/connect-url?integration_key=${encodeURIComponent(integrationKey)}`;
        if (redirectUri) {
            url += `&redirect_uri=${encodeURIComponent(redirectUri)}`;
        }
        return this.http.get<MembraneConnectUrlResponse>(url);
    }

    // ── Convenience: Open Connection in New Window ────────────────

    /** Redirect the browser to Pipedream hosted connection UI. */
    openConnection(integrationKey: string, redirectUri?: string): void {
        this.getConnectUrl(integrationKey, redirectUri).subscribe({
            next: (res) => {
                window.location.href = res.url;
            },
            error: (err) => {
                console.error('Failed to get Pipedream connect URL', err);
            },
        });
    }

    /** Disconnect a Pipedream connection.
     *
     * `integrationKey` is optional but recommended: it ensures the backend
     * resolves the tenantKey with the correct scope (per-user vs per-org).
     */
    disconnect(connectionId: string, integrationKey?: string): Observable<void> {
        let url = `${API_URL}/pipedream/connections/${encodeURIComponent(connectionId)}`;
        if (integrationKey) {
            url += `?integration_key=${encodeURIComponent(integrationKey)}`;
        }
        return this.http.delete<void>(url);
    }

    // ── Platform Configuration ───────────────────────────────────

    getConfig(): Observable<MembraneConfigResponse> {
        return this.http.get<MembraneConfigResponse>(`${API_URL}/pipedream/config`);
    }

    updateConfig(config: MembraneConfig): Observable<MembraneConfigResponse> {
        return this.http.put<MembraneConfigResponse>(`${API_URL}/pipedream/config`, config);
    }
}
