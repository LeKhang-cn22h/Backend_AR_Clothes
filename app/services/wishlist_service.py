from typing import Optional
from fastapi import HTTPException
from models.wishlist import Wishlist
from repositories.wishlist_repository import WishlistRepository
from repositories.user_repository import UserRepository
from schemas.wishlist import WishlistCreate


class WishlistService:
    def __init__(self, repo: WishlistRepository, user_repo: UserRepository):
        self.repo = repo
        self.user_repo = user_repo

    async def add(self, data: WishlistCreate) -> Wishlist:
        user = await self.user_repo.get_by_id(data.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung")
        existing = await self.repo.get_by_user_and_product(data.user_id, data.firestore_product_id)
        if existing:
            raise HTTPException(status_code=409, detail="San pham da co trong wishlist")
        return await self.repo.create(data)

    async def get_all(self, user_id: Optional[int] = None, skip: int = 0, limit: int = 20) -> list[Wishlist]:
        return await self.repo.get_all(user_id=user_id, skip=skip, limit=limit)

    async def delete(self, id: int) -> None:
        deleted = await self.repo.delete(id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Khong tim thay muc wishlist")

    async def delete_by_product(self, user_id: int, firestore_product_id: str) -> None:
        deleted = await self.repo.delete_by_product(user_id, firestore_product_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Khong tim thay muc wishlist")

    async def check(self, user_id: int, firestore_product_id: str) -> dict:
        wishlist = await self.repo.get_by_user_and_product(user_id, firestore_product_id)
        return {
            "is_wishlisted": wishlist is not None,
            "wishlist_id": wishlist.id if wishlist else None,
        }
