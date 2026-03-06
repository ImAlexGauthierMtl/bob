"""KB repository — data access layer for Knowledge Base."""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.domain.entities.kb_article import KBArticle, KBCategory, ArticleVisibility


class KBRepository:
    """Repository for Knowledge Base data access with visibility filtering."""

    def __init__(self, db: Session):
        self.db = db

    # ── Categories ───────────────────────────────

    def create_category(self, category: KBCategory) -> KBCategory:
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def list_categories(self, tenant_id: str) -> List[KBCategory]:
        return (
            self.db.query(KBCategory)
            .filter(KBCategory.tenant_id == tenant_id)
            .order_by(KBCategory.sort_order, KBCategory.name)
            .all()
        )

    def get_category_by_id(self, category_id: str, tenant_id: str) -> Optional[KBCategory]:
        return (
            self.db.query(KBCategory)
            .filter(KBCategory.id == category_id, KBCategory.tenant_id == tenant_id)
            .first()
        )

    def update_category_article_count(self, category_id: str, tenant_id: str) -> None:
        """Recalculate article_count for a category."""
        count = (
            self.db.query(KBArticle)
            .filter(
                KBArticle.category_id == category_id,
                KBArticle.tenant_id == tenant_id,
                KBArticle.is_deleted == False,
                KBArticle.is_published == True,
            )
            .count()
        )
        cat = self.get_category_by_id(category_id, tenant_id)
        if cat:
            cat.article_count = count
            self.db.commit()

    # ── Articles ─────────────────────────────────

    def create_article(self, article: KBArticle) -> KBArticle:
        self.db.add(article)
        self.db.commit()
        self.db.refresh(article)
        # Update category count
        if article.category_id:
            self.update_category_article_count(article.category_id, article.tenant_id)
        return article

    def get_article_by_id(self, article_id: str, tenant_id: str) -> Optional[KBArticle]:
        return (
            self.db.query(KBArticle)
            .filter(
                KBArticle.id == article_id,
                KBArticle.tenant_id == tenant_id,
                KBArticle.is_deleted == False,
            )
            .first()
        )

    def get_article_by_slug(self, slug: str, tenant_id: str) -> Optional[KBArticle]:
        return (
            self.db.query(KBArticle)
            .filter(
                KBArticle.slug == slug,
                KBArticle.tenant_id == tenant_id,
                KBArticle.is_deleted == False,
            )
            .first()
        )

    def list_articles(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        category_id: Optional[str] = None,
        visibility: Optional[str] = None,
        published_only: bool = True,
    ) -> List[KBArticle]:
        query = self.db.query(KBArticle).filter(
            KBArticle.tenant_id == tenant_id,
            KBArticle.is_deleted == False,
        )
        if published_only:
            query = query.filter(KBArticle.is_published == True)
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                (KBArticle.title.ilike(pattern)) | (KBArticle.excerpt.ilike(pattern))
            )
        if category_id:
            query = query.filter(KBArticle.category_id == category_id)
        if visibility:
            query = query.filter(KBArticle.visibility == visibility)
        return (
            query.order_by(KBArticle.is_featured.desc(), KBArticle.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_articles(
        self,
        tenant_id: str,
        category_id: Optional[str] = None,
        visibility: Optional[str] = None,
        published_only: bool = True,
    ) -> int:
        query = self.db.query(KBArticle).filter(
            KBArticle.tenant_id == tenant_id,
            KBArticle.is_deleted == False,
        )
        if published_only:
            query = query.filter(KBArticle.is_published == True)
        if category_id:
            query = query.filter(KBArticle.category_id == category_id)
        if visibility:
            query = query.filter(KBArticle.visibility == visibility)
        return query.count()

    def popular_articles(self, tenant_id: str, limit: int = 10) -> List[KBArticle]:
        return (
            self.db.query(KBArticle)
            .filter(
                KBArticle.tenant_id == tenant_id,
                KBArticle.is_deleted == False,
                KBArticle.is_published == True,
            )
            .order_by(KBArticle.view_count.desc())
            .limit(limit)
            .all()
        )

    def increment_view_count(self, article: KBArticle) -> None:
        article.view_count = (article.view_count or 0) + 1
        self.db.commit()

    def record_feedback(self, article: KBArticle, helpful: bool) -> None:
        if helpful:
            article.helpful_yes = (article.helpful_yes or 0) + 1
        else:
            article.helpful_no = (article.helpful_no or 0) + 1
        self.db.commit()

    def update_article(self, article: KBArticle) -> KBArticle:
        article.version += 1
        self.db.commit()
        self.db.refresh(article)
        return article

    def soft_delete_article(self, article: KBArticle, deleted_by: str) -> KBArticle:
        from datetime import datetime, timezone
        old_category_id = article.category_id
        article.is_deleted = True
        article.deleted_at = datetime.now(timezone.utc)
        article.deleted_by = deleted_by
        article.version += 1
        self.db.commit()
        self.db.refresh(article)
        if old_category_id:
            self.update_category_article_count(old_category_id, article.tenant_id)
        return article

    # ── Stats ────────────────────────────────────

    def get_stats(self, tenant_id: str) -> dict:
        base = self.db.query(KBArticle).filter(
            KBArticle.tenant_id == tenant_id,
            KBArticle.is_deleted == False,
        )
        total = base.count()
        published = base.filter(KBArticle.is_published == True).count()
        total_views = self.db.query(func.coalesce(func.sum(KBArticle.view_count), 0)).filter(
            KBArticle.tenant_id == tenant_id, KBArticle.is_deleted == False,
        ).scalar()
        total_yes = self.db.query(func.coalesce(func.sum(KBArticle.helpful_yes), 0)).filter(
            KBArticle.tenant_id == tenant_id, KBArticle.is_deleted == False,
        ).scalar()
        total_no = self.db.query(func.coalesce(func.sum(KBArticle.helpful_no), 0)).filter(
            KBArticle.tenant_id == tenant_id, KBArticle.is_deleted == False,
        ).scalar()
        total_feedback = total_yes + total_no
        avg_helpfulness = round((total_yes / total_feedback * 100), 1) if total_feedback > 0 else 0.0
        categories = self.db.query(KBCategory).filter(KBCategory.tenant_id == tenant_id).count()
        return {
            "total_articles": total,
            "published_articles": published,
            "total_categories": categories,
            "total_views": total_views,
            "avg_helpfulness": avg_helpfulness,
        }
