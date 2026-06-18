import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface PlatformOverview {
    user_id?: string;
    tenant_id?: string;
    workflows: unknown[];
    recent_executions: unknown[];
    monitoring: Record<string, unknown>;
    usage: Record<string, unknown>;
    totals: Record<string, number>;
}

@Injectable({ providedIn: 'root' })
export class PlatformB4fService {
    private http = inject(HttpClient);

    getOverview(): Observable<PlatformOverview> {
        return this.http.get<PlatformOverview>(`${environment.platformApiUrl}/overview`);
    }
}
