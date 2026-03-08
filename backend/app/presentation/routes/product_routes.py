"""Product routes — CRUD API."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.domain.entities.product import Product
from app.infrastructure.persistence.product_repository import ProductRepository
from app.presentation.schemas.product_schemas import (
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse,
)

router = APIRouter(prefix="/api/v1/products")


@router.get("", response_model=ProductListResponse)
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    category: Optional[str] = None,
    parent_product_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ProductRepository(db)
    items = repo.list_all(current_user["tenant_id"], skip, limit, search, category, parent_product_id)
    total = repo.count(current_user["tenant_id"], category, parent_product_id)
    return ProductListResponse(
        items=[ProductResponse.model_validate(i) for i in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/services", response_model=list[ProductResponse])
async def list_service_products(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List active SERVICE products — used for add-on parent selection."""
    repo = ProductRepository(db)
    items = repo.list_services(current_user["tenant_id"])
    return [ProductResponse.model_validate(i) for i in items]


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ProductRepository(db)
    product = Product(
        **data.model_dump(exclude_none=True),
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
    )
    created = repo.create(product)
    return ProductResponse.model_validate(created)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ProductRepository(db)
    product = repo.get_by_id(product_id, current_user["tenant_id"])
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ProductResponse.model_validate(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    data: ProductUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ProductRepository(db)
    product = repo.get_by_id(product_id, current_user["tenant_id"])
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(product, k, v)
    product.updated_by = current_user["email"]
    return ProductResponse.model_validate(repo.update(product))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ProductRepository(db)
    product = repo.get_by_id(product_id, current_user["tenant_id"])
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    repo.soft_delete(product, current_user["email"])
