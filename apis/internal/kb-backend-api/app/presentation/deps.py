"""Presentation dependencies for KB API."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.use_cases.kb_use_cases import KBUseCases
from app.events.publishers import publish_article_created, publish_article_deleted, publish_article_updated
from app.infrastructure.database import get_db
from app.infrastructure.persistence.kb_repository import KBRepository
from app.infrastructure.persistence.models.kb_article import KBArticle, KBCategory


def get_kb_use_cases(db: Session = Depends(get_db)) -> KBUseCases:
    return KBUseCases(
        repo=KBRepository(db),
        create_category_entity=KBCategory,
        create_article_entity=KBArticle,
        publish_article_created=publish_article_created,
        publish_article_updated=publish_article_updated,
        publish_article_deleted=publish_article_deleted,
    )
