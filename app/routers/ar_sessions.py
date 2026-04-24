from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from repositories.ar_session_repository import ARSessionRepository
from repositories.garment_repository import GarmentRepository
from schemas.ar_session import ARSessionCreate, ARSessionResponse, ARSessionStatsResponse
from services.ar_session_service import ARSessionService

router = APIRouter(prefix="/ar-sessions", tags=["AR Sessions"])


def get_service(db: AsyncSession = Depends(get_db)) -> ARSessionService:
    return ARSessionService(ARSessionRepository(db), GarmentRepository(db))


@router.post("", response_model=ARSessionResponse, status_code=status.HTTP_201_CREATED)
async def create(payload: ARSessionCreate, service: ARSessionService = Depends(get_service)):
    return await service.create(payload)


@router.get("/stats/summary", response_model=ARSessionStatsResponse)
async def get_stats(service: ARSessionService = Depends(get_service)):
    return await service.get_stats()


@router.get("", response_model=list[ARSessionResponse])
async def get_all(
    user_id: Optional[int] = Query(default=None),
    garment_id: Optional[int] = Query(default=None),
    converted: Optional[bool] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: ARSessionService = Depends(get_service),
):
    return await service.get_all(
        user_id=user_id, garment_id=garment_id, converted=converted, skip=skip, limit=limit
    )


@router.get("/{id}", response_model=ARSessionResponse)
async def get_one(id: int, service: ARSessionService = Depends(get_service)):
    return await service.get_by_id(id)


@router.patch("/{id}/converted", response_model=ARSessionResponse)
async def mark_converted(id: int, service: ARSessionService = Depends(get_service)):
    return await service.mark_converted(id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(id: int, service: ARSessionService = Depends(get_service)):
    await service.delete(id)
