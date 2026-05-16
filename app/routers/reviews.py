# routers/reviews.py
import json
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


def parse_media_urls(raw: Optional[str]) -> Optional[list[str]]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return []


# ── POST ─────────────────────────────────────────────────────────
@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create(payload: ReviewCreate, service: ReviewService = Depends(get_service)):
    review = await service.create(payload)
    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        firestore_product_id=review.firestore_product_id,
        rating=review.rating,
        comment=review.comment,
        media_urls=parse_media_urls(review.media_urls),
        created_at=review.created_at,
        updated_at=review.updated_at,
        is_deleted=review.is_deleted,
    )


# ── GET /product/{id}/stats ───────────────────────────────────────
@router.get("/product/{firestore_product_id}/stats", response_model=ReviewStatsResponse)
async def get_product_stats(
    firestore_product_id: str,
    service: ReviewService = Depends(get_service),
):
    return await service.get_product_stats(firestore_product_id)


# ── GET /product/{id} ─────────────────────────────────────────────
@router.get("/product/{firestore_product_id}", response_model=list[ReviewResponse])
async def get_by_product(
    firestore_product_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=5, ge=1, le=100),
    service: ReviewService = Depends(get_service),
):
    skip = (page - 1) * limit
    return await service.get_all(
        firestore_product_id=firestore_product_id,
        skip=skip,
        limit=limit,
    )


# ── GET /check-purchase/{id} ──────────────────────────────────────
@router.get("/check-purchase/{firestore_product_id}")
async def check_purchase(
    firestore_product_id: str,
    user_id: int = Query(...),
    service: ReviewService = Depends(get_service),
):
    existing = await service.get_user_review(user_id, firestore_product_id)
    return {"hasPurchased": True, "hasReviewed": existing is not None}


# ── GET /my-review/{id} ───────────────────────────────────────────
@router.get("/my-review/{firestore_product_id}", response_model=Optional[ReviewResponse])
async def get_my_review(
    firestore_product_id: str,
    user_id: int = Query(...),
    service: ReviewService = Depends(get_service),
):
    review = await service.get_user_review(user_id, firestore_product_id)
    if not review:
        return None
    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        firestore_product_id=review.firestore_product_id,
        rating=review.rating,
        comment=review.comment,
        media_urls=parse_media_urls(review.media_urls),
        created_at=review.created_at,
        updated_at=review.updated_at,
        is_deleted=review.is_deleted,
    )


# ── GET all ───────────────────────────────────────────────────────
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


# ── GET /{id} ─────────────────────────────────────────────────────
@router.get("/{id}", response_model=ReviewResponse)
async def get_one(id: int, service: ReviewService = Depends(get_service)):
    review = await service.get_by_id(id)
    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        firestore_product_id=review.firestore_product_id,
        rating=review.rating,
        comment=review.comment,
        media_urls=parse_media_urls(review.media_urls),
        created_at=review.created_at,
        updated_at=review.updated_at,
        is_deleted=review.is_deleted,
    )


# ── PUT /{id} ─────────────────────────────────────────────────────
@router.put("/{id}", response_model=ReviewResponse)
async def update(
    id: int,
    payload: ReviewUpdate,
    service: ReviewService = Depends(get_service),
):
    review = await service.update(id, payload)
    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        firestore_product_id=review.firestore_product_id,
        rating=review.rating,
        comment=review.comment,
        media_urls=parse_media_urls(review.media_urls),
        created_at=review.created_at,
        updated_at=review.updated_at,
        is_deleted=review.is_deleted,
    )


# ── DELETE /{id} ──────────────────────────────────────────────────
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(id: int, service: ReviewService = Depends(get_service)):
    await service.delete(id)