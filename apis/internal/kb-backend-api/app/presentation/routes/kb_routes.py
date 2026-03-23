"""KB CRUD routes — pure storage, no business logic."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.domain.entities.kb_article import KBArticle, KBCategory
from app.infrastructure.persistence.kb_repository import KBRepository
from app.events.publishers import publish_article_created, publish_article_updated, publish_article_deleted
from app.presentation.schemas.kb_schemas import (
    CategoryCreate, CategoryUpdate, CategoryResponse, CategoryListResponse,
    ArticleCreate, ArticleUpdate, ArticleResponse, ArticleSummaryResponse,
    ArticleListResponse, FeedbackRequest, KBStatsResponse,
)

router = APIRouter(prefix="/api/v1/kb")


# ── Categories ───────────────────────────────────────

@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    cats = repo.list_categories(user["tenant_id"])
    return CategoryListResponse(
        items=[CategoryResponse.model_validate(c) for c in cats],
        total=len(cats),
    )


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    cat = KBCategory(
        **data.model_dump(exclude_none=True),
        tenant_id=user["tenant_id"],
        created_by=user["email"],
    )
    created = repo.create_category(cat)
    return CategoryResponse.model_validate(created)


@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    cat = repo.get_category_by_id(category_id, user["tenant_id"])
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryResponse.model_validate(cat)


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    cat = repo.get_category_by_id(category_id, user["tenant_id"])
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(cat, k, v)
    cat.updated_by = user["email"]
    updated = repo.update_category(cat)
    return CategoryResponse.model_validate(updated)


# ── Articles — List & Search ─────────────────────────

@router.get("/articles", response_model=ArticleListResponse)
async def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    visibility: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    items = repo.list_articles(
        user["tenant_id"], skip, limit, search, category_id, visibility,
    )
    total = repo.count_articles(
        user["tenant_id"], category_id, visibility,
    )
    return ArticleListResponse(
        items=[ArticleSummaryResponse.model_validate(a) for a in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/articles/popular", response_model=list[ArticleSummaryResponse])
async def popular_articles(
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    items = repo.popular_articles(user["tenant_id"], limit)
    return [ArticleSummaryResponse.model_validate(a) for a in items]


# ── Articles — CRUD ──────────────────────────────────

@router.post("/articles", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    data: ArticleCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    article = KBArticle(
        **data.model_dump(exclude_none=True),
        tenant_id=user["tenant_id"],
        created_by=user["email"],
    )
    created = repo.create_article(article)
    await publish_article_created(created.id, {"title": created.title, "tenant_id": created.tenant_id})
    return ArticleResponse.model_validate(created)


@router.get("/articles/{slug_or_id}", response_model=ArticleResponse)
async def get_article(
    slug_or_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    article = repo.get_article_by_slug(slug_or_id, user["tenant_id"])
    if not article:
        article = repo.get_article_by_id(slug_or_id, user["tenant_id"])
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    repo.increment_view_count(article)
    return ArticleResponse.model_validate(article)


@router.patch("/articles/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    article = repo.get_article_by_id(article_id, user["tenant_id"])
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    old_category = article.category_id
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(article, k, v)
    article.updated_by = user["email"]
    updated = repo.update_article(article)
    if old_category != updated.category_id:
        if old_category:
            repo.update_category_article_count(old_category, user["tenant_id"])
        if updated.category_id:
            repo.update_category_article_count(updated.category_id, user["tenant_id"])
    await publish_article_updated(updated.id, {"fields": list(data.model_dump(exclude_unset=True).keys())})
    return ArticleResponse.model_validate(updated)


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    article = repo.get_article_by_id(article_id, user["tenant_id"])
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    repo.soft_delete_article(article, user["email"])
    await publish_article_deleted(article_id)


# ── Feedback ─────────────────────────────────────────

@router.post("/articles/{article_id}/feedback", status_code=status.HTTP_200_OK)
async def article_feedback(
    article_id: str,
    data: FeedbackRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    article = repo.get_article_by_id(article_id, user["tenant_id"])
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    repo.record_feedback(article, data.helpful)
    return {"status": "ok", "helpful_yes": article.helpful_yes, "helpful_no": article.helpful_no}


# ── Stats ────────────────────────────────────────────

@router.get("/stats", response_model=KBStatsResponse)
async def get_stats(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    stats = repo.get_stats(user["tenant_id"])
    return KBStatsResponse(**stats)
