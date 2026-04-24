from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from repositories.review_repository import ReviewRepository
from schemas.review import ReviewCreate, ReviewUpdate, ReviewResponse, ReviewStatsResponse
from services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])


def get_service(db: AsyncSession = Depends(get_db)) -> ReviewService:
    return ReviewService(ReviewRepository(db))


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create(payload: ReviewCreate, service: ReviewService = Depends(get_service)):
    return await service.create(payload)


@router.get("/product/{firestore_product_id}/stats", response_model=ReviewStatsResponse)
async def get_product_stats(firestore_product_id: str, service: ReviewService = Depends(get_service)):
    return await service.get_product_stats(firestore_product_id)


@router.get("", response_model=list[ReviewResponse])
async def get_all(
    firestore_product_id: Optional[str] = Query(default=None),
    user_id: Optional[int] = Query(default=None),
    rating: Optional[int] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: ReviewService = Depends(get_service),
):
    return await service.get_all(
        firestore_product_id=firestore_product_id,
        user_id=user_id,
        rating=rating,
        skip=skip,
        limit=limit,
    )


@router.get("/{id}", response_model=ReviewResponse)
async def get_one(id: int, service: ReviewService = Depends(get_service)):
    return await service.get_by_id(id)


@router.put("/{id}", response_model=ReviewResponse)
async def update(id: int, payload: ReviewUpdate, service: ReviewService = Depends(get_service)):
    return await service.update(id, payload)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(id: int, service: ReviewService = Depends(get_service)):
    await service.delete(id)
