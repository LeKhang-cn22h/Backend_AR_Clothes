from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.product_view import ProductView
from schemas.product_view import ProductViewCreate


class ProductViewRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ProductViewCreate) -> ProductView:
        view = ProductView(**data.model_dump())
        self.db.add(view)
        await self.db.commit()
        await self.db.refresh(view)
        return view

    async def get_by_id(self, id: int) -> Optional[ProductView]:
        result = await self.db.execute(select(ProductView).where(ProductView.id == id))
        return result.scalar_one_or_none()

    async def get_all(
        self,
        firestore_product_id: Optional[str] = None,
        user_id: Optional[int] = None,
        source: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ProductView]:
        query = select(ProductView)
        if firestore_product_id:
            query = query.where(ProductView.firestore_product_id == firestore_product_id)
        if user_id is not None:
            query = query.where(ProductView.user_id == user_id)
        if source:
            query = query.where(ProductView.source == source)
        query = query.offset(skip).limit(limit).order_by(ProductView.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_product(self, firestore_product_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ProductView).where(
                ProductView.firestore_product_id == firestore_product_id
            )
        )
        return result.scalar_one()

    async def get_top_products(self, limit: int = 10) -> list[dict]:
        query = (
            select(ProductView.firestore_product_id, func.count(ProductView.id).label("view_count"))
            .group_by(ProductView.firestore_product_id)
            .order_by(func.count(ProductView.id).desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return [
            {"firestore_product_id": row.firestore_product_id, "view_count": row.view_count}
            for row in result.all()
        ]

    async def delete(self, id: int) -> bool:
        view = await self.get_by_id(id)
        if not view:
            return False
        await self.db.delete(view)
        await self.db.commit()
        return True

    async def count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(ProductView))
        return result.scalar_one()

    async def update(self, id: int, **kwargs) -> Optional[ProductView]:
        view = await self.get_by_id(id)
        if not view:
            return None
        for field, value in kwargs.items():
            setattr(view, field, value)
        await self.db.commit()
        await self.db.refresh(view)
        return view
