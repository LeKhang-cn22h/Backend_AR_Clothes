from typing import Optional
from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from models.wishlist import Wishlist
from schemas.wishlist import WishlistCreate


class WishlistRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: WishlistCreate) -> Wishlist:
        wishlist = Wishlist(**data.model_dump())
        self.db.add(wishlist)
        await self.db.commit()
        await self.db.refresh(wishlist)
        return wishlist

    async def get_by_id(self, id: int) -> Optional[Wishlist]:
        result = await self.db.execute(select(Wishlist).where(Wishlist.id == id))
        return result.scalar_one_or_none()

    async def get_by_user_and_product(self, user_id: int, firestore_product_id: str) -> Optional[Wishlist]:
        result = await self.db.execute(
            select(Wishlist).where(
                Wishlist.user_id == user_id,
                Wishlist.firestore_product_id == firestore_product_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(self, user_id: Optional[int] = None, skip: int = 0, limit: int = 20) -> list[Wishlist]:
        query = select(Wishlist)
        if user_id is not None:
            query = query.where(Wishlist.user_id == user_id)
        query = query.offset(skip).limit(limit).order_by(Wishlist.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete(self, id: int) -> bool:
        wishlist = await self.get_by_id(id)
        if not wishlist:
            return False
        await self.db.delete(wishlist)
        await self.db.commit()
        return True

    async def delete_by_product(self, user_id: int, firestore_product_id: str) -> bool:
        result = await self.db.execute(
            sa_delete(Wishlist).where(
                Wishlist.user_id == user_id,
                Wishlist.firestore_product_id == firestore_product_id,
            )
        )
        await self.db.commit()
        return result.rowcount > 0

    async def count(self, user_id: Optional[int] = None) -> int:
        query = select(func.count()).select_from(Wishlist)
        if user_id is not None:
            query = query.where(Wishlist.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def update(self, id: int, **kwargs) -> Optional[Wishlist]:
        wishlist = await self.get_by_id(id)
        if not wishlist:
            return None
        for field, value in kwargs.items():
            setattr(wishlist, field, value)
        await self.db.commit()
        await self.db.refresh(wishlist)
        return wishlist
