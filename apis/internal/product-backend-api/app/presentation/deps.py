"""Presentation dependencies for Product API."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.use_cases.product_use_cases import ProductUseCases
from app.events.publishers import publish_product_created, publish_product_updated
from app.infrastructure.database import get_db
from app.infrastructure.persistence.models.product import Product
from app.infrastructure.persistence.product_repository import ProductRepository


def get_product_use_cases(db: Session = Depends(get_db)) -> ProductUseCases:
    return ProductUseCases(
        repo=ProductRepository(db),
        create_product_entity=Product,
        publish_created=publish_product_created,
        publish_updated=publish_product_updated,
    )
