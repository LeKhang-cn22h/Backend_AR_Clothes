from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from repositories.product_view_repository import ProductViewRepository
from schemas.product_view import ProductViewCreate, ProductViewResponse, ProductViewCountResponse, TopProductResponse
from services.product_view_service import ProductViewService

router = APIRouter(prefix="/product-views", tags=["Product Views"])


def get_service(db: AsyncSession = Depends(get_db)) -> ProductViewService:
    return ProductViewService(ProductViewRepository(db))


@router.post("", response_model=ProductViewResponse, status_code=status.HTTP_201_CREATED)
async def record(payload: ProductViewCreate, service: ProductViewService = Depends(get_service)):
    return await service.record(payload)


@router.get("/product/{firestore_product_id}/count", response_model=ProductViewCountResponse)
async def count_by_product(firestore_product_id: str, service: ProductViewService = Depends(get_service)):
    return await service.count_by_product(firestore_product_id)


@router.get("/stats/top-products", response_model=list[TopProductResponse])
async def top_products(
    limit: int = Query(default=10, ge=1, le=100),
    service: ProductViewService = Depends(get_service),
):
    return await service.get_top_products(limit=limit)


@router.get("", response_model=list[ProductViewResponse])
async def get_all(
    firestore_product_id: Optional[str] = Query(default=None),
    user_id: Optional[int] = Query(default=None),
    source: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: ProductViewService = Depends(get_service),
):
    return await service.get_all(
        firestore_product_id=firestore_product_id,
        user_id=user_id,
        source=source,
        skip=skip,
        limit=limit,
    )
