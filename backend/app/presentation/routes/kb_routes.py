"""Knowledge Base routes — CRUD API with visibility filtering."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.domain.entities.kb_article import KBArticle, KBCategory
from app.infrastructure.persistence.kb_repository import KBRepository
from app.presentation.schemas.kb_schemas import (
    CategoryCreate, CategoryResponse, CategoryListResponse,
    ArticleCreate, ArticleUpdate, ArticleResponse, ArticleSummaryResponse,
    ArticleListResponse, FeedbackRequest, KBStatsResponse,
)

router = APIRouter(prefix="/api/v1/kb")


# ── Categories ───────────────────────────────────────

@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    cats = repo.list_categories(current_user["tenant_id"])
    return CategoryListResponse(
        items=[CategoryResponse.model_validate(c) for c in cats],
        total=len(cats),
    )


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    cat = KBCategory(
        **data.model_dump(exclude_none=True),
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
    )
    created = repo.create_category(cat)
    return CategoryResponse.model_validate(created)


# ── Articles — List & Search ─────────────────────────

@router.get("/articles", response_model=ArticleListResponse)
async def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    visibility: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    items = repo.list_articles(
        current_user["tenant_id"], skip, limit, search, category_id, visibility,
    )
    total = repo.count_articles(
        current_user["tenant_id"], category_id, visibility,
    )
    return ArticleListResponse(
        items=[ArticleSummaryResponse.model_validate(a) for a in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/articles/popular", response_model=list[ArticleSummaryResponse])
async def popular_articles(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    items = repo.popular_articles(current_user["tenant_id"], limit)
    return [ArticleSummaryResponse.model_validate(a) for a in items]


# ── Articles — CRUD ──────────────────────────────────

@router.post("/articles", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    data: ArticleCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    article = KBArticle(
        **data.model_dump(exclude_none=True),
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
    )
    created = repo.create_article(article)
    return ArticleResponse.model_validate(created)


@router.get("/articles/{slug}", response_model=ArticleResponse)
async def get_article(
    slug: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    article = repo.get_article_by_slug(slug, current_user["tenant_id"])
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    # Increment view count
    repo.increment_view_count(article)
    return ArticleResponse.model_validate(article)


@router.patch("/articles/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    article = repo.get_article_by_id(article_id, current_user["tenant_id"])
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    old_category = article.category_id
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(article, k, v)
    article.updated_by = current_user["email"]
    updated = repo.update_article(article)
    # Update category counts if category changed
    if old_category != updated.category_id:
        if old_category:
            repo.update_category_article_count(old_category, current_user["tenant_id"])
        if updated.category_id:
            repo.update_category_article_count(updated.category_id, current_user["tenant_id"])
    return ArticleResponse.model_validate(updated)


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    article = repo.get_article_by_id(article_id, current_user["tenant_id"])
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    repo.soft_delete_article(article, current_user["email"])


# ── Feedback ─────────────────────────────────────────

@router.post("/articles/{article_id}/feedback", status_code=status.HTTP_200_OK)
async def article_feedback(
    article_id: str,
    data: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    article = repo.get_article_by_id(article_id, current_user["tenant_id"])
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    repo.record_feedback(article, data.helpful)
    return {"status": "ok", "helpful_yes": article.helpful_yes, "helpful_no": article.helpful_no}


# ── Stats ────────────────────────────────────────────

@router.get("/stats", response_model=KBStatsResponse)
async def get_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = KBRepository(db)
    stats = repo.get_stats(current_user["tenant_id"])
    return KBStatsResponse(**stats)
