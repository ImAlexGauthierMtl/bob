import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ActivityListResponse } from '../models/activity.model';
import { ContactListResponse } from '../models/contact.model';
import { OpportunityListResponse } from '../models/opportunity.model';
import { OrganizationListResponse } from '../models/organization.model';

export interface CrmDashboardSummary {
    user_id?: string;
    tenant_id?: string;
    totals: Record<string, number>;
    highlights: Record<string, unknown[]>;
    next_actions: Array<{ type: string; label: string; count: number }>;
}

export interface CrmListQuery {
    skip: number;
    limit: number;
}

export interface CrmContactsQuery extends CrmListQuery {
    organizationId?: string;
}

export interface CrmOpportunitiesQuery extends CrmContactsQuery {
    stage?: string;
}

export interface CrmActivitiesQuery extends CrmContactsQuery {
    contactId?: string;
    opportunityId?: string;
    status?: string;
}

@Injectable({ providedIn: 'root' })
export class CrmB4fService {
    private http = inject(HttpClient);

    getDashboardSummary(): Observable<CrmDashboardSummary> {
        return this.http.get<CrmDashboardSummary>(`${environment.crmApiUrl}/dashboard/summary`);
    }

    getOrganizations(query: CrmListQuery): Observable<OrganizationListResponse> {
        return this.http.get<OrganizationListResponse>(`${environment.crmApiUrl}/organizations`, {
            params: this.listParams(query),
        });
    }

    getContacts(query: CrmContactsQuery): Observable<ContactListResponse> {
        let params = this.listParams(query);
        if (query.organizationId) params = params.set('organization_id', query.organizationId);
        return this.http.get<ContactListResponse>(`${environment.crmApiUrl}/contacts`, {
            params,
        });
    }

    getOpportunities(query: CrmOpportunitiesQuery): Observable<OpportunityListResponse> {
        let params = this.listParams(query);
        if (query.organizationId) params = params.set('organization_id', query.organizationId);
        if (query.stage) params = params.set('stage', query.stage);
        return this.http.get<OpportunityListResponse>(`${environment.crmApiUrl}/opportunities`, { params });
    }

    getActivities(query: CrmActivitiesQuery): Observable<ActivityListResponse> {
        let params = this.listParams(query);
        if (query.organizationId) params = params.set('organization_id', query.organizationId);
        if (query.contactId) params = params.set('contact_id', query.contactId);
        if (query.opportunityId) params = params.set('opportunity_id', query.opportunityId);
        if (query.status) params = params.set('activity_status', query.status);
        return this.http.get<ActivityListResponse>(`${environment.crmApiUrl}/activities`, { params });
    }

    private listParams(query: CrmListQuery): HttpParams {
        return new HttpParams()
            .set('skip', query.skip)
            .set('limit', query.limit);
    }
}
