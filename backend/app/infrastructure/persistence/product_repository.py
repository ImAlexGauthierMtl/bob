"""Product repository — data access layer."""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.entities.product import Product


class ProductRepository:
    """Repository for product data access."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def get_by_id(self, product_id: str, tenant_id: str) -> Optional[Product]:
        return self.db.query(Product).filter(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
            Product.is_deleted == False,
        ).first()

    def list_all(
        self, tenant_id: str, skip: int = 0, limit: int = 50,
        search: Optional[str] = None, category: Optional[str] = None,
        parent_product_id: Optional[str] = None,
    ) -> List[Product]:
        query = self.db.query(Product).filter(
            Product.tenant_id == tenant_id, Product.is_deleted == False,
        )
        if search:
            query = query.filter(
                (Product.name.ilike(f"%{search}%")) | (Product.sku.ilike(f"%{search}%"))
            )
        if category:
            query = query.filter(Product.category == category)
        if parent_product_id:
            query = query.filter(Product.parent_product_id == parent_product_id)
        return query.order_by(Product.name).offset(skip).limit(limit).all()

    def count(
        self, tenant_id: str, category: Optional[str] = None,
        parent_product_id: Optional[str] = None,
    ) -> int:
        query = self.db.query(Product).filter(
            Product.tenant_id == tenant_id, Product.is_deleted == False,
        )
        if category:
            query = query.filter(Product.category == category)
        if parent_product_id:
            query = query.filter(Product.parent_product_id == parent_product_id)
        return query.count()

    def list_services(self, tenant_id: str) -> List[Product]:
        """List SERVICE products for add-on parent selection."""
        return self.db.query(Product).filter(
            Product.tenant_id == tenant_id,
            Product.is_deleted == False,
            Product.category == "SERVICE",
            Product.is_active == True,
        ).order_by(Product.name).all()

    def update(self, product: Product) -> Product:
        product.version += 1
        self.db.commit()
        self.db.refresh(product)
        return product

    def soft_delete(self, product: Product, deleted_by: str, reason: Optional[str] = None) -> Product:
        from datetime import datetime, timezone
        product.is_deleted = True
        product.deleted_at = datetime.now(timezone.utc)
        product.deleted_by = deleted_by
        product.deleted_reason = reason
        product.version += 1
        self.db.commit()
        self.db.refresh(product)
        return product
