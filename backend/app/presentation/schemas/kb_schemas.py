"""KB schemas — Pydantic models for Knowledge Base API."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── Category ─────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = 0


class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    article_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    items: List[CategoryResponse]
    total: int


# ── Article ──────────────────────────────────────

class ArticleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    slug: str = Field(..., min_length=1, max_length=500)
    excerpt: Optional[str] = None
    content: str = ""
    category_id: Optional[str] = None
    tags: Optional[List[str]] = []
    visibility: Optional[str] = "shared"
    required_module: Optional[str] = None
    required_role: Optional[str] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    author_avatar: Optional[str] = None
    read_time_minutes: Optional[int] = 5
    is_published: Optional[bool] = False
    is_featured: Optional[bool] = False


class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    slug: Optional[str] = Field(None, min_length=1, max_length=500)
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
    content: Optional[str] = None
    category_id: Optional[str] = None
    tags: Optional[List[str]] = []
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
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArticleSummaryResponse(BaseModel):
    """Lighter response for list views — no content body."""
    id: str
    title: str
    slug: str
    excerpt: Optional[str] = None
    category_id: Optional[str] = None
    tags: Optional[List[str]] = []
    visibility: str = "shared"
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    read_time_minutes: int = 5
    view_count: int = 0
    is_published: bool = False
    is_featured: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    items: List[ArticleSummaryResponse]
    total: int
    skip: int
    limit: int


class FeedbackRequest(BaseModel):
    helpful: bool


class KBStatsResponse(BaseModel):
    total_articles: int
    published_articles: int
    total_categories: int
    total_views: int
    avg_helpfulness: float
