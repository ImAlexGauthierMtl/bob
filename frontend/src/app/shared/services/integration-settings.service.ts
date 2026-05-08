import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
    IntegrationSetting,
    IntegrationSettingCreate,
    IntegrationSettingUpdate,
    IntegrationSettingListResponse,
} from '../models/integration-setting.model';

const API_URL = `${environment.communicationApiUrl}`;

@Injectable({ providedIn: 'root' })
export class IntegrationSettingsService {
    private http = inject(HttpClient);

    list(): Observable<IntegrationSettingListResponse> {
        return this.http.get<IntegrationSettingListResponse>(`${API_URL}/integration-settings`);
    }

    upsert(data: IntegrationSettingCreate): Observable<IntegrationSetting> {
        return this.http.post<IntegrationSetting>(`${API_URL}/integration-settings`, data);
    }

    update(integrationKey: string, data: IntegrationSettingUpdate): Observable<IntegrationSetting> {
        return this.http.patch<IntegrationSetting>(`${API_URL}/integration-settings/${integrationKey}`, data);
    }

    delete(integrationKey: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/integration-settings/${integrationKey}`);
    }
}
