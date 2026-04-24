from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from repositories.garment_category_repository import GarmentCategoryRepository
from schemas.garment_category import GarmentCategoryCreate, GarmentCategoryUpdate, GarmentCategoryResponse
from services.garment_category_service import GarmentCategoryService

router = APIRouter(prefix="/garment-categories", tags=["Garment Categories"])


def get_service(db: AsyncSession = Depends(get_db)) -> GarmentCategoryService:
    return GarmentCategoryService(GarmentCategoryRepository(db))


@router.post("", response_model=GarmentCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create(payload: GarmentCategoryCreate, service: GarmentCategoryService = Depends(get_service)):
    return await service.create(payload)


@router.get("", response_model=list[GarmentCategoryResponse])
async def get_all(service: GarmentCategoryService = Depends(get_service)):
    return await service.get_all()


@router.get("/{id}", response_model=GarmentCategoryResponse)
async def get_one(id: int, service: GarmentCategoryService = Depends(get_service)):
    return await service.get_by_id(id)


@router.put("/{id}", response_model=GarmentCategoryResponse)
async def update(id: int, payload: GarmentCategoryUpdate, service: GarmentCategoryService = Depends(get_service)):
    return await service.update(id, payload)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(id: int, service: GarmentCategoryService = Depends(get_service)):
    await service.delete(id)
