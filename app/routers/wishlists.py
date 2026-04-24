from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from repositories.wishlist_repository import WishlistRepository
from repositories.user_repository import UserRepository
from schemas.wishlist import WishlistCreate, WishlistResponse, WishlistCheckResponse
from services.wishlist_service import WishlistService

router = APIRouter(prefix="/wishlists", tags=["Wishlists"])


def get_service(db: AsyncSession = Depends(get_db)) -> WishlistService:
    return WishlistService(WishlistRepository(db), UserRepository(db))


@router.post("", response_model=WishlistResponse, status_code=status.HTTP_201_CREATED)
async def add(payload: WishlistCreate, service: WishlistService = Depends(get_service)):
    return await service.add(payload)


@router.get("/check", response_model=WishlistCheckResponse)
async def check(
    user_id: int = Query(...),
    firestore_product_id: str = Query(...),
    service: WishlistService = Depends(get_service),
):
    return await service.check(user_id, firestore_product_id)


@router.get("", response_model=list[WishlistResponse])
async def get_all(
    user_id: Optional[int] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: WishlistService = Depends(get_service),
):
    return await service.get_all(user_id=user_id, skip=skip, limit=limit)


@router.delete("/product/{firestore_product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_by_product(
    firestore_product_id: str,
    user_id: int = Query(...),
    service: WishlistService = Depends(get_service),
):
    await service.delete_by_product(user_id, firestore_product_id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(id: int, service: WishlistService = Depends(get_service)):
    await service.delete(id)
