import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface KbHome {
    user_id?: string;
    tenant_id?: string;
    categories: unknown[];
    recent_articles: unknown[];
    popular_articles: unknown[];
    stats: Record<string, unknown>;
    empty_state: { show_create_article_hint: boolean; message?: string | null };
}

@Injectable({ providedIn: 'root' })
export class KbB4fService {
    private http = inject(HttpClient);

    getHome(): Observable<KbHome> {
        return this.http.get<KbHome>(`${environment.kbApiUrl}/kb/home`);
    }
}
