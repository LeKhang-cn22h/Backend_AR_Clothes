from typing import Optional
from fastapi import HTTPException
from models.review import Review
from repositories.review_repository import ReviewRepository
from schemas.review import ReviewCreate, ReviewUpdate


class ReviewService:
    def __init__(self, repo: ReviewRepository):
        self.repo = repo

    async def create(self, data: ReviewCreate) -> Review:
        existing = await self.repo.get_by_user_and_product(
            data.user_id, data.firestore_product_id
        )
        if existing:
            # Đã review rồi → update thay vì báo lỗi
            update_data = ReviewUpdate(rating=data.rating, comment=data.comment)
            updated = await self.repo.update(existing.id, update_data)
            return updated
        return await self.repo.create(data)

    async def get_user_review(
        self, user_id: int, firestore_product_id: str
    ) -> Optional[Review]:
        return await self.repo.get_by_user_and_product(user_id, firestore_product_id)

    async def get_by_id(self, id: int) -> Review:
        review = await self.repo.get_by_id(id)
        if not review:
            raise HTTPException(status_code=404, detail="Khong tim thay danh gia")
        return review

    async def get_all(
        self,
        firestore_product_id: Optional[str] = None,
        user_id:              Optional[int] = None,
        rating:               Optional[int] = None,
        skip:  int = 0,
        limit: int = 20,
    ) -> list[Review]:
        return await self.repo.get_all(
            firestore_product_id=firestore_product_id,
            user_id=user_id,
            rating=rating,
            skip=skip,
            limit=limit,
        )

    async def update(self, id: int, data: ReviewUpdate) -> Review:
        review = await self.repo.update(id, data)
        if not review:
            raise HTTPException(status_code=404, detail="Khong tim thay danh gia")
        return review

    async def delete(self, id: int) -> None:
        deleted = await self.repo.delete(id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Khong tim thay danh gia")

    async def get_product_stats(self, firestore_product_id: str) -> dict:
        return await self.repo.get_stats(firestore_product_id)