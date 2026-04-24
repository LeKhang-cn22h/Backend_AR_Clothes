from fastapi import HTTPException
from models.garment_category import GarmentCategory
from repositories.garment_category_repository import GarmentCategoryRepository
from schemas.garment_category import GarmentCategoryCreate, GarmentCategoryUpdate


class GarmentCategoryService:
    def __init__(self, repo: GarmentCategoryRepository):
        self.repo = repo

    async def create(self, data: GarmentCategoryCreate) -> GarmentCategory:
        return await self.repo.create(data)

    async def get_by_id(self, id: int) -> GarmentCategory:
        category = await self.repo.get_by_id(id)
        if not category:
            raise HTTPException(status_code=404, detail="Khong tim thay danh muc")
        return category

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[GarmentCategory]:
        return await self.repo.get_all(skip=skip, limit=limit)

    async def update(self, id: int, data: GarmentCategoryUpdate) -> GarmentCategory:
        category = await self.repo.update(id, data)
        if not category:
            raise HTTPException(status_code=404, detail="Khong tim thay danh muc")
        return category

    async def delete(self, id: int) -> None:
        deleted = await self.repo.delete(id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Khong tim thay danh muc")
