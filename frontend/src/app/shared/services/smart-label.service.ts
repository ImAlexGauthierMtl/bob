import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { SmartLabel, SmartLabelListResponse } from '../models/smart-label.model';

const API_URL = `${environment.apiUrl}/inbox/labels`;

@Injectable({ providedIn: 'root' })
export class SmartLabelService {
    private http = inject(HttpClient);

    getAll(skip = 0, limit = 50): Observable<SmartLabelListResponse> {
        return this.http.get<SmartLabelListResponse>(`${API_URL}?skip=${skip}&limit=${limit}`);
    }

    getById(id: string): Observable<SmartLabel> {
        return this.http.get<SmartLabel>(`${API_URL}/${id}`);
    }

    create(label: Partial<SmartLabel> & { name: string; color: string }): Observable<SmartLabel> {
        return this.http.post<SmartLabel>(API_URL, label);
    }

    update(id: string, label: Partial<SmartLabel>): Observable<SmartLabel> {
        return this.http.patch<SmartLabel>(`${API_URL}/${id}`, label);
    }

    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/${id}`);
    }
}
