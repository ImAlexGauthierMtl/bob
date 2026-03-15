import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Quote, QuoteListResponse, CreateQuoteDto } from '../models/quote.model';

const API_URL = `${environment.crmApiUrl}`;

@Injectable({ providedIn: 'root' })
export class QuoteService {
    private http = inject(HttpClient);

    getAll(skip = 0, limit = 50, opportunityId?: string, organizationId?: string): Observable<QuoteListResponse> {
        let url = `${API_URL}/quotes?skip=${skip}&limit=${limit}`;
        if (opportunityId) url += `&opportunity_id=${opportunityId}`;
        if (organizationId) url += `&organization_id=${organizationId}`;
        return this.http.get<QuoteListResponse>(url);
    }

    getById(id: string): Observable<Quote> {
        return this.http.get<Quote>(`${API_URL}/quotes/${id}`);
    }

    create(data: CreateQuoteDto): Observable<Quote> {
        return this.http.post<Quote>(`${API_URL}/quotes`, data);
    }

    update(id: string, data: Partial<CreateQuoteDto>): Observable<Quote> {
        return this.http.patch<Quote>(`${API_URL}/quotes/${id}`, data);
    }

    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/quotes/${id}`);
    }
}
