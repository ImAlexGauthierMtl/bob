import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
    ToolGovernancePolicy,
    ToolGovernancePolicyListResponse,
    ToolGovernancePolicyUpdate,
    UserToolAccessResponse,
    UserToolPreferences,
    UserToolPreferencesUpdate,
} from '../models/tool-governance.model';

const API_URL = `${environment.agentControlApiUrl}`;

@Injectable({ providedIn: 'root' })
export class ToolGovernanceService {
    private http = inject(HttpClient);

    listPolicies(): Observable<ToolGovernancePolicyListResponse> {
        return this.http.get<ToolGovernancePolicyListResponse>(`${API_URL}/tool-governance/policies`);
    }

    updatePolicy(policyId: string, payload: ToolGovernancePolicyUpdate): Observable<ToolGovernancePolicy> {
        return this.http.put<ToolGovernancePolicy>(
            `${API_URL}/tool-governance/policies/${encodeURIComponent(policyId)}`,
            payload,
        );
    }

    getMyAccess(): Observable<UserToolAccessResponse> {
        return this.http.get<UserToolAccessResponse>(`${API_URL}/tool-governance/me`);
    }

    updateMyPreferences(payload: UserToolPreferencesUpdate): Observable<UserToolPreferences> {
        return this.http.put<UserToolPreferences>(`${API_URL}/tool-governance/me/preferences`, payload);
    }
}
