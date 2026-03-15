"""KB Schemas — Pydantic models for Knowledge Base API."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Category schemas
class KBCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None

class KBCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class KBCategoryResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    class Config:
        from_attributes = True

# Aliases for import compatibility
CategoryCreate = KBCategoryCreate
CategoryUpdate = KBCategoryUpdate
CategoryResponse = KBCategoryResponse

class CategoryListResponse(BaseModel):
    items: List[CategoryResponse]
    total: int
    skip: int = 0
    limit: int = 50

# Article schemas
class KBArticleCreate(BaseModel):
    title: str
    content: Optional[str] = None
    category_id: Optional[str] = None
    visibility: Optional[str] = "draft"

class KBArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category_id: Optional[str] = None
    visibility: Optional[str] = None

class KBArticleResponse(BaseModel):
    id: str
    title: str
    content: Optional[str] = None
    category_id: Optional[str] = None
    visibility: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# Aliases for import compatibility
ArticleCreate = KBArticleCreate
ArticleUpdate = KBArticleUpdate
ArticleResponse = KBArticleResponse

class ArticleSummaryResponse(BaseModel):
    id: str
    title: str
    content: Optional[str] = None
    class Config:
        from_attributes = True

class ArticleListResponse(BaseModel):
    items: List[ArticleResponse]
    total: int
    skip: int = 0
    limit: int = 50

class FeedbackRequest(BaseModel):
    article_id: str
    rating: int
    comment: Optional[str] = None

class KBStatsResponse(BaseModel):
    total_articles: int
    total_categories: int
    total_views: int
