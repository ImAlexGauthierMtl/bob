import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface CommunicationIntegrationOverview {
    user_id?: string;
    tenant_id?: string;
    integrations: Array<{
        integration_key: string;
        display_name?: string;
        scope_mode?: string;
        is_enabled: boolean;
        is_connected: boolean;
        connection_id?: string;
        connection_provider?: string;
    }>;
    smart_labels: unknown[];
    totals: Record<string, number>;
}

@Injectable({ providedIn: 'root' })
export class CommunicationB4fService {
    private http = inject(HttpClient);

    getIntegrationOverview(): Observable<CommunicationIntegrationOverview> {
        return this.http.get<CommunicationIntegrationOverview>(`${environment.communicationApiUrl}/integrations/overview`);
    }
}
