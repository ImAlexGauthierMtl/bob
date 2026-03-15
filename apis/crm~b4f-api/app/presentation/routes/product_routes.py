"""Product routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.product_repository import ProductRepository
from app.domain.entities.product import Product
from app.presentation.schemas.crm_schemas import ProductCreate, ProductUpdate, ProductResponse, ProductListResponse

router = APIRouter(prefix="/api/v1/products")

@router.get("", response_model=ProductListResponse)
async def list_products(skip: int = 0, limit: int = 50, category: str = Query(None),
                         user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ProductRepository(db)
    items = repo.list_all(user["tenant_id"], skip, limit, category)
    total = repo.count(user["tenant_id"])
    return ProductListResponse(items=[ProductResponse.model_validate(p) for p in items], total=total, skip=skip, limit=limit)

@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(data: ProductCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ProductRepository(db)
    product = Product(**data.model_dump(), tenant_id=user["tenant_id"], created_by=user["email"])
    return ProductResponse.model_validate(repo.create(product))

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ProductRepository(db)
    product = repo.get_by_id(product_id, user["tenant_id"])
    if not product: raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.model_validate(product)

@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: str, data: ProductUpdate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ProductRepository(db)
    product = repo.get_by_id(product_id, user["tenant_id"])
    if not product: raise HTTPException(status_code=404, detail="Product not found")
    for k, v in data.model_dump(exclude_unset=True).items(): setattr(product, k, v)
    product.updated_by = user["email"]
    return ProductResponse.model_validate(repo.update(product))

@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ProductRepository(db)
    product = repo.get_by_id(product_id, user["tenant_id"])
    if not product: raise HTTPException(status_code=404, detail="Product not found")
    repo.soft_delete(product, user["email"])
