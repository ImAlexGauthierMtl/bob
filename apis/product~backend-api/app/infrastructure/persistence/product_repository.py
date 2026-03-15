"""Product repository — data access layer."""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.domain.entities.product import Product


class ProductRepository:
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
        category: Optional[str] = None, active_only: bool = True,
    ) -> List[Product]:
        q = self.db.query(Product).filter(Product.tenant_id == tenant_id, Product.is_deleted == False)
        if active_only:
            q = q.filter(Product.is_active == True)
        if category:
            q = q.filter(Product.category == category)
        return q.order_by(Product.name).offset(skip).limit(limit).all()

    def count(self, tenant_id: str, active_only: bool = True) -> int:
        q = self.db.query(Product).filter(Product.tenant_id == tenant_id, Product.is_deleted == False)
        if active_only:
            q = q.filter(Product.is_active == True)
        return q.count()

    def update(self, product: Product) -> Product:
        product.version += 1
        self.db.commit()
        self.db.refresh(product)
        return product

    def soft_delete(self, product: Product, deleted_by: str) -> Product:
        from datetime import datetime, timezone
        product.is_deleted = True
        product.deleted_at = datetime.now(timezone.utc)
        product.deleted_by = deleted_by
        product.version += 1
        self.db.commit()
        self.db.refresh(product)
        return product
