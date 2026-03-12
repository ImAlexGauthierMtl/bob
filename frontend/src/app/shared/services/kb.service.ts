import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
    KBCategory, KBArticle, KBArticleSummary,
    CategoryListResponse, ArticleListResponse, KBStats,
} from '../models/kb.model';

const API_URL = `${environment.apiUrl}`;

@Injectable({ providedIn: 'root' })
export class KnowledgeBaseService {
    private http = inject(HttpClient);

    // ── Categories ──────────────────────────────

    listCategories(): Observable<CategoryListResponse> {
        return this.http.get<CategoryListResponse>(`${API_URL}/kb/categories`);
    }

    // ── Articles ────────────────────────────────

    listArticles(params?: {
        skip?: number;
        limit?: number;
        search?: string;
        category_id?: string;
        visibility?: string;
    }): Observable<ArticleListResponse> {
        let url = `${API_URL}/kb/articles?skip=${params?.skip ?? 0}&limit=${params?.limit ?? 20}`;
        if (params?.search) url += `&search=${encodeURIComponent(params.search)}`;
        if (params?.category_id) url += `&category_id=${params.category_id}`;
        if (params?.visibility) url += `&visibility=${params.visibility}`;
        return this.http.get<ArticleListResponse>(url);
    }

    popularArticles(limit = 10): Observable<KBArticleSummary[]> {
        return this.http.get<KBArticleSummary[]>(`${API_URL}/kb/articles/popular?limit=${limit}`);
    }

    getArticle(slug: string): Observable<KBArticle> {
        return this.http.get<KBArticle>(`${API_URL}/kb/articles/${slug}`);
    }

    sendFeedback(articleId: string, helpful: boolean): Observable<{ helpful_yes: number; helpful_no: number }> {
        return this.http.post<{ helpful_yes: number; helpful_no: number }>(
            `${API_URL}/kb/articles/${articleId}/feedback`,
            { helpful }
        );
    }

    // ── Stats ───────────────────────────────────

    getStats(): Observable<KBStats> {
        return this.http.get<KBStats>(`${API_URL}/kb/stats`);
    }
}
