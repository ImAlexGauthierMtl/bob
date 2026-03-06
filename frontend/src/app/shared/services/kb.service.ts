import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

// ── Interfaces ──────────────────────────────────

export interface KBCategory {
    id: string;
    name: string;
    slug: string;
    description: string | null;
    icon: string | null;
    color: string | null;
    sort_order: number;
    article_count: number;
    created_at: string;
    updated_at: string;
}

export interface KBArticleSummary {
    id: string;
    title: string;
    slug: string;
    excerpt: string | null;
    category_id: string | null;
    tags: string[];
    visibility: 'internal' | 'shared' | 'public';
    author_name: string | null;
    author_role: string | null;
    read_time_minutes: number;
    view_count: number;
    is_published: boolean;
    is_featured: boolean;
    created_at: string;
    updated_at: string;
}

export interface KBArticle extends KBArticleSummary {
    content: string | null;
    required_module: string | null;
    required_role: string | null;
    author_avatar: string | null;
    helpful_yes: number;
    helpful_no: number;
}

export interface CategoryListResponse {
    items: KBCategory[];
    total: number;
}

export interface ArticleListResponse {
    items: KBArticleSummary[];
    total: number;
    skip: number;
    limit: number;
}

export interface KBStats {
    total_articles: number;
    published_articles: number;
    total_categories: number;
    total_views: number;
    avg_helpfulness: number;
}

const API_URL = 'http://localhost:8555/api/v1';

@Injectable({ providedIn: 'root' })
export class KnowledgeBaseService {
    constructor(private http: HttpClient) { }

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
