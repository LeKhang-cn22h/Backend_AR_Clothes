from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.garment_category import GarmentCategory
from schemas.garment_category import GarmentCategoryCreate, GarmentCategoryUpdate


class GarmentCategoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: GarmentCategoryCreate) -> GarmentCategory:
        category = GarmentCategory(**data.model_dump())
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def get_by_id(self, id: int) -> Optional[GarmentCategory]:
        result = await self.db.execute(select(GarmentCategory).where(GarmentCategory.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[GarmentCategory]:
        result = await self.db.execute(
            select(GarmentCategory).offset(skip).limit(limit).order_by(GarmentCategory.id)
        )
        return list(result.scalars().all())

    async def update(self, id: int, data: GarmentCategoryUpdate) -> Optional[GarmentCategory]:
        category = await self.get_by_id(id)
        if not category:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(category, field, value)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def delete(self, id: int) -> bool:
        category = await self.get_by_id(id)
        if not category:
            return False
        await self.db.delete(category)
        await self.db.commit()
        return True

    async def count(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(GarmentCategory))
        return result.scalar_one()
