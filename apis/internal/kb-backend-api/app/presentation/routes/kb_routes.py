"""KB CRUD routes — pure storage, no business logic."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.application.use_cases.kb_use_cases import KBUseCases
from app.domain.exceptions import ArticleNotFoundError, CategoryNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_kb_use_cases
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
    use_cases: KBUseCases = Depends(get_kb_use_cases),
):
    result = await use_cases.list_categories(user["tenant_id"])
    return CategoryListResponse(
        items=[CategoryResponse.model_validate(c) for c in result.items],
        total=result.total,
    )


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    user: dict = Depends(get_current_user),
    use_cases: KBUseCases = Depends(get_kb_use_cases),
):
    created = await use_cases.create_category(data.model_dump(exclude_none=True), user)
    return CategoryResponse.model_validate(created)


@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: str,
    user: dict = Depends(get_current_user),
    use_cases: KBUseCases = Depends(get_kb_use_cases),
):
    try:
        category = await use_cases.get_category(category_id, user["tenant_id"])
    except CategoryNotFoundError:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryResponse.model_validate(category)


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    user: dict = Depends(get_current_user),
    use_cases: KBUseCases = Depends(get_kb_use_cases),
):
    try:
        updated = await use_cases.update_category(
            category_id,
            data.model_dump(exclude_unset=True),
            user,
        )
    except CategoryNotFoundError:
        raise HTTPException(status_code=404, detail="Category not found")
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
    use_cases: KBUseCases = Depends(get_kb_use_cases),
):
    result = await use_cases.list_articles(
        user["tenant_id"],
        skip,
        limit,
        search,
        category_id,
        visibility,
    )
    return ArticleListResponse(
        items=[ArticleSummaryResponse.model_validate(a) for a in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.get("/articles/popular", response_model=list[ArticleSummaryResponse])
async def popular_articles(
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user),
    use_cases: KBUseCases = Depends(get_kb_use_cases),
):
    items = await use_cases.popular_articles(user["tenant_id"], limit)
    return [ArticleSummaryResponse.model_validate(a) for a in items]


# ── Articles — CRUD ──────────────────────────────────

@router.post("/articles", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    data: ArticleCreate,
    user: dict = Depends(get_current_user),
    use_cases: KBUseCases = Depends(get_kb_use_cases),
):
    created = await use_cases.create_article(data.model_dump(exclude_none=True), user)
    return ArticleResponse.model_validate(created)


@router.get("/articles/{slug_or_id}", response_model=ArticleResponse)
async def get_article(
    slug_or_id: str,
    user: dict = Depends(get_current_user),
    use_cases: KBUseCases = Depends(get_kb_use_cases),
):
    try:
        article = await use_cases.get_article(slug_or_id, user["tenant_id"])
    except ArticleNotFoundError:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleResponse.model_validate(article)


@router.patch("/articles/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    user: dict = Depends(get_current_user),
    use_cases: KBUseCases = Depends(get_kb_use_cases),
):
    try:
        updated = await use_cases.update_article(
            article_id,
            data.model_dump(exclude_unset=True),
            user,
        )
    except ArticleNotFoundError:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleResponse.model_validate(updated)


@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str,
    user: dict = Depends(get_current_user),
    use_cases: KBUseCases = Depends(get_kb_use_cases),
):
    try:
        await use_cases.delete_article(article_id, user)
    except ArticleNotFoundError:
        raise HTTPException(status_code=404, detail="Article not found")


# ── Feedback ─────────────────────────────────────────

@router.post("/articles/{article_id}/feedback", status_code=status.HTTP_200_OK)
async def article_feedback(
    article_id: str,
    data: FeedbackRequest,
    user: dict = Depends(get_current_user),
    use_cases: KBUseCases = Depends(get_kb_use_cases),
):
    try:
        return await use_cases.record_feedback(article_id, data.helpful, user)
    except ArticleNotFoundError:
        raise HTTPException(status_code=404, detail="Article not found")


# ── Stats ────────────────────────────────────────────

@router.get("/stats", response_model=KBStatsResponse)
async def get_stats(
    user: dict = Depends(get_current_user),
    use_cases: KBUseCases = Depends(get_kb_use_cases),
):
    stats = await use_cases.get_stats(user["tenant_id"])
    return KBStatsResponse(**stats)
