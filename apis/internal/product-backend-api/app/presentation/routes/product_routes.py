"""Product HTTP routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.application.use_cases.product_use_cases import ProductUseCases
from app.domain.exceptions import ProductNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_product_use_cases
from app.presentation.schemas.product_schemas import (
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse,
)

router = APIRouter(prefix="/api/v1/products")


@router.get("", response_model=ProductListResponse)
async def list_products(
    skip: int = 0, limit: int = 50, category: str = Query(None),
    user: dict = Depends(get_current_user),
    use_cases: ProductUseCases = Depends(get_product_use_cases),
):
    result = await use_cases.list_products(user["tenant_id"], skip, limit, category)
    return ProductListResponse(
        items=[ProductResponse.model_validate(product) for product in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    user: dict = Depends(get_current_user),
    use_cases: ProductUseCases = Depends(get_product_use_cases),
):
    created = await use_cases.create_product(data.model_dump(), user)
    return ProductResponse.model_validate(created)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    user: dict = Depends(get_current_user),
    use_cases: ProductUseCases = Depends(get_product_use_cases),
):
    try:
        product = await use_cases.get_product(product_id, user["tenant_id"])
    except ProductNotFoundError:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.model_validate(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str, data: ProductUpdate,
    user: dict = Depends(get_current_user),
    use_cases: ProductUseCases = Depends(get_product_use_cases),
):
    try:
        updated = await use_cases.update_product(
            product_id,
            data.model_dump(exclude_unset=True),
            user,
        )
    except ProductNotFoundError:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.model_validate(updated)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    user: dict = Depends(get_current_user),
    use_cases: ProductUseCases = Depends(get_product_use_cases),
):
    try:
        await use_cases.delete_product(product_id, user)
    except ProductNotFoundError:
        raise HTTPException(status_code=404, detail="Product not found")
