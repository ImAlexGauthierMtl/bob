"""KB schemas — Pydantic models for KB Backend API."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── Category ───────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    article_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    items: List[CategoryResponse]
    total: int


# ── Article ────────────────────────────────────────

class ArticleCreate(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str = ""
    category_id: Optional[str] = None
    tags: Optional[List[str]] = None
    visibility: str = "shared"
    required_module: Optional[str] = None
    required_role: Optional[str] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    author_avatar: Optional[str] = None
    read_time_minutes: int = 5
    is_published: bool = False
    is_featured: bool = False


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    category_id: Optional[str] = None
    tags: Optional[List[str]] = None
    visibility: Optional[str] = None
    required_module: Optional[str] = None
    required_role: Optional[str] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    author_avatar: Optional[str] = None
    read_time_minutes: Optional[int] = None
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None


class ArticleResponse(BaseModel):
    id: str
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str = ""
    category_id: Optional[str] = None
    tags: Optional[List[str]] = None
    visibility: str = "shared"
    required_module: Optional[str] = None
    required_role: Optional[str] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    author_avatar: Optional[str] = None
    read_time_minutes: int = 5
    view_count: int = 0
    helpful_yes: int = 0
    helpful_no: int = 0
    is_published: bool = False
    is_featured: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ArticleSummaryResponse(BaseModel):
    id: str
    title: str
    slug: str
    excerpt: Optional[str] = None
    category_id: Optional[str] = None
    visibility: str = "shared"
    author_name: Optional[str] = None
    read_time_minutes: int = 5
    view_count: int = 0
    is_featured: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    items: List[ArticleSummaryResponse]
    total: int
    skip: int = 0
    limit: int = 20


# ── Feedback ───────────────────────────────────────

class FeedbackRequest(BaseModel):
    helpful: bool


# ── Stats ──────────────────────────────────────────

class KBStatsResponse(BaseModel):
    total_articles: int
    published_articles: int
    total_categories: int
    total_views: int
    avg_helpfulness: float = 0.0
