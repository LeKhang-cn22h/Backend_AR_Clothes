from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.review import Review
from schemas.review import ReviewCreate, ReviewUpdate


class ReviewRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ReviewCreate) -> Review:
        review = Review(**data.model_dump())
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def get_by_id(self, id: int) -> Optional[Review]:
        result = await self.db.execute(select(Review).where(Review.id == id))
        return result.scalar_one_or_none()

    async def get_by_user_and_product(self, user_id: int, firestore_product_id: str) -> Optional[Review]:
        result = await self.db.execute(
            select(Review).where(
                Review.user_id == user_id,
                Review.firestore_product_id == firestore_product_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        firestore_product_id: Optional[str] = None,
        user_id: Optional[int] = None,
        rating: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Review]:
        query = select(Review)
        if firestore_product_id:
            query = query.where(Review.firestore_product_id == firestore_product_id)
        if user_id is not None:
            query = query.where(Review.user_id == user_id)
        if rating is not None:
            query = query.where(Review.rating == rating)
        query = query.offset(skip).limit(limit).order_by(Review.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(self, id: int, data: ReviewUpdate) -> Optional[Review]:
        review = await self.get_by_id(id)
        if not review:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(review, field, value)
        await self.db.commit()
        await self.db.refresh(review)
        return review

    async def delete(self, id: int) -> bool:
        review = await self.get_by_id(id)
        if not review:
            return False
        await self.db.delete(review)
        await self.db.commit()
        return True

    async def count(self, firestore_product_id: Optional[str] = None) -> int:
        query = select(func.count()).select_from(Review)
        if firestore_product_id:
            query = query.where(Review.firestore_product_id == firestore_product_id)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_stats(self, firestore_product_id: str) -> dict:
        agg = await self.db.execute(
            select(func.avg(Review.rating), func.count(Review.id)).where(
                Review.firestore_product_id == firestore_product_id
            )
        )
        row = agg.one()
        avg_rating = float(row[0]) if row[0] else 0.0
        total = row[1]

        dist_result = await self.db.execute(
            select(Review.rating, func.count(Review.id))
            .where(Review.firestore_product_id == firestore_product_id)
            .group_by(Review.rating)
        )
        distribution = {str(i): 0 for i in range(1, 6)}
        for r, c in dist_result.all():
            distribution[str(r)] = c

        return {"avg_rating": avg_rating, "total_reviews": total, "distribution": distribution}
