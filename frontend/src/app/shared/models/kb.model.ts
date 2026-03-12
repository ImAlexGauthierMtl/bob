// Knowledge Base model — mirrors backend KB Pydantic schemas

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
