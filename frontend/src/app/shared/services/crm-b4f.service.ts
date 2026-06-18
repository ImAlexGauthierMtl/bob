import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface CrmDashboardSummary {
    user_id?: string;
    tenant_id?: string;
    totals: Record<string, number>;
    highlights: Record<string, unknown[]>;
    next_actions: Array<{ type: string; label: string; count: number }>;
}

@Injectable({ providedIn: 'root' })
export class CrmB4fService {
    private http = inject(HttpClient);

    getDashboardSummary(): Observable<CrmDashboardSummary> {
        return this.http.get<CrmDashboardSummary>(`${environment.crmApiUrl}/dashboard/summary`);
    }
}
