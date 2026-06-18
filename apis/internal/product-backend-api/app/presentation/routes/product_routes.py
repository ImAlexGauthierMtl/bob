"""Product CRUD routes — pure storage, no business logic."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.product_repository import ProductRepository
from app.infrastructure.persistence.models.product import Product
from app.events.publishers import publish_product_created, publish_product_updated
from app.presentation.schemas.product_schemas import (
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse,
)

router = APIRouter(prefix="/api/v1/products")


@router.get("", response_model=ProductListResponse)
async def list_products(
    skip: int = 0, limit: int = 50, category: str = Query(None),
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = ProductRepository(db)
    items = repo.list_all(user["tenant_id"], skip, limit, category)
    total = repo.count(user["tenant_id"])
    return ProductListResponse(
        items=[ProductResponse.model_validate(p) for p in items],
        total=total, skip=skip, limit=limit,
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = ProductRepository(db)
    product = Product(**data.model_dump(), tenant_id=user["tenant_id"], created_by=user["email"])
    created = repo.create(product)
    await publish_product_created(created.id, {"name": created.name, "tenant_id": created.tenant_id})
    return ProductResponse.model_validate(created)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = ProductRepository(db)
    product = repo.get_by_id(product_id, user["tenant_id"])
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.model_validate(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str, data: ProductUpdate,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = ProductRepository(db)
    product = repo.get_by_id(product_id, user["tenant_id"])
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(product, k, v)
    product.updated_by = user["email"]
    updated = repo.update(product)
    await publish_product_updated(updated.id, {"fields": list(updates.keys())})
    return ProductResponse.model_validate(updated)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = ProductRepository(db)
    product = repo.get_by_id(product_id, user["tenant_id"])
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    repo.soft_delete(product, user["email"])
