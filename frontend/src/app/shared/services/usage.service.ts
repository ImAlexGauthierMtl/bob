import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface UsageLog {
    id: string;
    timestamp: string;
    service_type: string;
    provider: string;
    model: string;
    trigger_source: string;
    trigger_id: string;
    correlation_id: string;
    correlation_label: string;
    input_tokens: number;
    output_tokens: number;
    audio_seconds: number;
    characters: number;
    cogs_amount: number;
    cogs_currency: string;
    tenant_id: string;
    user_id: string;
    user_email: string;
    is_billable: boolean;
    metadata_?: Record<string, unknown> | null;
}

export interface UsageListResponse {
    items: UsageLog[];
    total: number;
    skip: number;
    limit: number;
}

export interface IntentGroup {
    correlation_id: string;
    correlation_label: string;
    transaction_count: number;
    total_cogs: number;
    first_timestamp: string;
    service_types: string[];
    trigger_source: string;
    tenant_id: string;
    user_email: string;
}

export interface IntentListResponse {
    items: IntentGroup[];
    total: number;
    skip: number;
    limit: number;
    total_cogs: number;
}

export interface UsageQuery {
    skip: number;
    limit: number;
    serviceType?: string;
    tenantId?: string;
}

@Injectable({ providedIn: 'root' })
export class UsageService {
    private http = inject(HttpClient);

    listUsage(query: UsageQuery): Observable<UsageListResponse> {
        return this.http.get<UsageListResponse>(`${environment.platformApiUrl}/admin/usage`, {
            params: this.usageParams(query),
        });
    }

    listIntents(query: Omit<UsageQuery, 'serviceType'>): Observable<IntentListResponse> {
        return this.http.get<IntentListResponse>(`${environment.platformApiUrl}/admin/usage/by-intent`, {
            params: this.usageParams(query),
        });
    }

    getIntentUsage(correlationId: string): Observable<UsageListResponse> {
        return this.http.get<UsageListResponse>(
            `${environment.platformApiUrl}/admin/usage/by-intent/${encodeURIComponent(correlationId)}`,
        );
    }

    private usageParams(query: UsageQuery | Omit<UsageQuery, 'serviceType'>): HttpParams {
        let params = new HttpParams()
            .set('skip', query.skip)
            .set('limit', query.limit);

        if ('serviceType' in query && query.serviceType) {
            params = params.set('service_type', query.serviceType);
        }
        if (query.tenantId) {
            params = params.set('tenant_id', query.tenantId);
        }
        return params;
    }
}
