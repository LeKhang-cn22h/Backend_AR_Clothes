from typing import Optional
from models.product_view import ProductView
from repositories.product_view_repository import ProductViewRepository
from schemas.product_view import ProductViewCreate


class ProductViewService:
    def __init__(self, repo: ProductViewRepository):
        self.repo = repo

    async def record(self, data: ProductViewCreate) -> ProductView:
        return await self.repo.create(data)

    async def get_all(
        self,
        firestore_product_id: Optional[str] = None,
        user_id: Optional[int] = None,
        source: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ProductView]:
        return await self.repo.get_all(
            firestore_product_id=firestore_product_id,
            user_id=user_id,
            source=source,
            skip=skip,
            limit=limit,
        )

    async def count_by_product(self, firestore_product_id: str) -> dict:
        count = await self.repo.count_by_product(firestore_product_id)
        return {"firestore_product_id": firestore_product_id, "view_count": count}

    async def get_top_products(self, limit: int = 10) -> list[dict]:
        return await self.repo.get_top_products(limit=limit)
