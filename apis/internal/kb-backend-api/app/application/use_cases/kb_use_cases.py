"""KB application use cases."""
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Protocol

from app.domain.exceptions import ArticleNotFoundError, CategoryNotFoundError


CategoryEntity = Any
ArticleEntity = Any
CategoryFactory = Callable[..., CategoryEntity]
ArticleFactory = Callable[..., ArticleEntity]
ArticlePublisher = Callable[[str, dict[str, Any]], Awaitable[None]]
ArticleDeletedPublisher = Callable[[str], Awaitable[None]]


class KBRepositoryPort(Protocol):
    def list_categories(self, tenant_id: str) -> list[CategoryEntity]:
        ...

    def create_category(self, category: CategoryEntity) -> CategoryEntity:
        ...

    def get_category_by_id(self, category_id: str, tenant_id: str) -> Optional[CategoryEntity]:
        ...

    def update_category(self, category: CategoryEntity) -> CategoryEntity:
        ...

    def list_articles(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        category_id: Optional[str] = None,
        visibility: Optional[str] = None,
    ) -> list[ArticleEntity]:
        ...

    def count_articles(
        self,
        tenant_id: str,
        category_id: Optional[str] = None,
        visibility: Optional[str] = None,
    ) -> int:
        ...

    def popular_articles(self, tenant_id: str, limit: int = 10) -> list[ArticleEntity]:
        ...

    def create_article(self, article: ArticleEntity) -> ArticleEntity:
        ...

    def get_article_by_slug(self, slug: str, tenant_id: str) -> Optional[ArticleEntity]:
        ...

    def get_article_by_id(self, article_id: str, tenant_id: str) -> Optional[ArticleEntity]:
        ...

    def increment_view_count(self, article: ArticleEntity) -> None:
        ...

    def update_article(self, article: ArticleEntity) -> ArticleEntity:
        ...

    def update_category_article_count(self, category_id: str, tenant_id: str) -> None:
        ...

    def soft_delete_article(self, article: ArticleEntity, deleted_by: str) -> ArticleEntity:
        ...

    def record_feedback(self, article: ArticleEntity, helpful: bool) -> None:
        ...

    def get_stats(self, tenant_id: str) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class CategoryListResult:
    items: list[CategoryEntity]
    total: int


@dataclass(frozen=True)
class ArticleListResult:
    items: list[ArticleEntity]
    total: int
    skip: int
    limit: int


class KBUseCases:
    def __init__(
        self,
        repo: KBRepositoryPort,
        create_category_entity: CategoryFactory,
        create_article_entity: ArticleFactory,
        publish_article_created: ArticlePublisher,
        publish_article_updated: ArticlePublisher,
        publish_article_deleted: ArticleDeletedPublisher,
    ) -> None:
        self.repo = repo
        self.create_category_entity = create_category_entity
        self.create_article_entity = create_article_entity
        self.publish_article_created = publish_article_created
        self.publish_article_updated = publish_article_updated
        self.publish_article_deleted = publish_article_deleted

    async def list_categories(self, tenant_id: str) -> CategoryListResult:
        categories = self.repo.list_categories(tenant_id)
        return CategoryListResult(items=categories, total=len(categories))

    async def create_category(self, data: dict[str, Any], user: dict[str, Any]) -> CategoryEntity:
        category = self.create_category_entity(
            **data,
            tenant_id=user["tenant_id"],
            created_by=user["email"],
        )
        return self.repo.create_category(category)

    async def get_category(self, category_id: str, tenant_id: str) -> CategoryEntity:
        category = self.repo.get_category_by_id(category_id, tenant_id)
        if not category:
            raise CategoryNotFoundError
        return category

    async def update_category(
        self,
        category_id: str,
        updates: dict[str, Any],
        user: dict[str, Any],
    ) -> CategoryEntity:
        category = await self.get_category(category_id, user["tenant_id"])
        for key, value in updates.items():
            setattr(category, key, value)
        category.updated_by = user["email"]
        return self.repo.update_category(category)

    async def list_articles(
        self,
        tenant_id: str,
        skip: int,
        limit: int,
        search: Optional[str],
        category_id: Optional[str],
        visibility: Optional[str],
    ) -> ArticleListResult:
        return ArticleListResult(
            items=self.repo.list_articles(tenant_id, skip, limit, search, category_id, visibility),
            total=self.repo.count_articles(tenant_id, category_id, visibility),
            skip=skip,
            limit=limit,
        )

    async def popular_articles(self, tenant_id: str, limit: int) -> list[ArticleEntity]:
        return self.repo.popular_articles(tenant_id, limit)

    async def create_article(self, data: dict[str, Any], user: dict[str, Any]) -> ArticleEntity:
        article = self.create_article_entity(
            **data,
            tenant_id=user["tenant_id"],
            created_by=user["email"],
        )
        created = self.repo.create_article(article)
        await self.publish_article_created(created.id, {"title": created.title, "tenant_id": created.tenant_id})
        return created

    async def get_article(self, slug_or_id: str, tenant_id: str) -> ArticleEntity:
        article = self.repo.get_article_by_slug(slug_or_id, tenant_id)
        if not article:
            article = self.repo.get_article_by_id(slug_or_id, tenant_id)
        if not article:
            raise ArticleNotFoundError
        self.repo.increment_view_count(article)
        return article

    async def update_article(
        self,
        article_id: str,
        updates: dict[str, Any],
        user: dict[str, Any],
    ) -> ArticleEntity:
        article = self.repo.get_article_by_id(article_id, user["tenant_id"])
        if not article:
            raise ArticleNotFoundError
        old_category = article.category_id
        for key, value in updates.items():
            setattr(article, key, value)
        article.updated_by = user["email"]
        updated = self.repo.update_article(article)
        if old_category != updated.category_id:
            if old_category:
                self.repo.update_category_article_count(old_category, user["tenant_id"])
            if updated.category_id:
                self.repo.update_category_article_count(updated.category_id, user["tenant_id"])
        await self.publish_article_updated(updated.id, {"fields": list(updates.keys())})
        return updated

    async def delete_article(self, article_id: str, user: dict[str, Any]) -> None:
        article = self.repo.get_article_by_id(article_id, user["tenant_id"])
        if not article:
            raise ArticleNotFoundError
        self.repo.soft_delete_article(article, user["email"])
        await self.publish_article_deleted(article_id)

    async def record_feedback(
        self,
        article_id: str,
        helpful: bool,
        user: dict[str, Any],
    ) -> dict[str, Any]:
        article = self.repo.get_article_by_id(article_id, user["tenant_id"])
        if not article:
            raise ArticleNotFoundError
        self.repo.record_feedback(article, helpful)
        return {
            "status": "ok",
            "helpful_yes": article.helpful_yes,
            "helpful_no": article.helpful_no,
        }

    async def get_stats(self, tenant_id: str) -> dict[str, Any]:
        return self.repo.get_stats(tenant_id)
