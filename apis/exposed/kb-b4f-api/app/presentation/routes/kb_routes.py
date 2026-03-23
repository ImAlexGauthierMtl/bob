"""KB routes — proxies to kb~backend-api."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.infrastructure.clients.kb_client import kb_client
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/kb")


# ── Categories ───────────────────────────────────────

@router.get("/categories")
async def list_categories(request: Request, user: dict = Depends(get_current_user)):
    return await kb_client.list_categories(forward_headers=request.headers)


@router.post("/categories", status_code=201)
async def create_category(data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await kb_client.create_category(data, forward_headers=request.headers)


@router.get("/categories/{category_id}")
async def get_category(category_id: str, request: Request, user: dict = Depends(get_current_user)):
    result = await kb_client.get_category(category_id, forward_headers=request.headers)
    if not result:
        raise HTTPException(status_code=404, detail="Category not found")
    return result


@router.patch("/categories/{category_id}")
async def update_category(category_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await kb_client.update_category(category_id, data, forward_headers=request.headers)


# ── Articles — List & Search ─────────────────────────

@router.get("/articles")
async def list_articles(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    visibility: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    return await kb_client.list_articles(skip, limit, search, category_id, visibility, forward_headers=request.headers)


@router.get("/articles/popular")
async def popular_articles(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    return await kb_client.popular_articles(limit, forward_headers=request.headers)


# ── Articles — CRUD ──────────────────────────────────

@router.post("/articles", status_code=201)
async def create_article(data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await kb_client.create_article(data, forward_headers=request.headers)


@router.get("/articles/{slug}")
async def get_article(slug: str, request: Request, user: dict = Depends(get_current_user)):
    result = await kb_client.get_article(slug, forward_headers=request.headers)
    if not result:
        raise HTTPException(status_code=404, detail="Article not found")
    return result


@router.patch("/articles/{article_id}")
async def update_article(article_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await kb_client.update_article(article_id, data, forward_headers=request.headers)


@router.delete("/articles/{article_id}", status_code=204)
async def delete_article(article_id: str, request: Request, user: dict = Depends(get_current_user)):
    await kb_client.delete_article(article_id, forward_headers=request.headers)


# ── Feedback ─────────────────────────────────────────

@router.post("/articles/{article_id}/feedback")
async def article_feedback(article_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await kb_client.article_feedback(article_id, data, forward_headers=request.headers)


# ── Stats ────────────────────────────────────────────

@router.get("/stats")
async def get_stats(request: Request, user: dict = Depends(get_current_user)):
    return await kb_client.get_stats(forward_headers=request.headers)
