from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
from models.conversion_event import ConversionEventType
from repositories.conversion_event_repository import ConversionEventRepository
from schemas.conversion_event import ConversionEventCreate, ConversionEventResponse, FunnelResponse, OverviewResponse
from services.conversion_event_service import ConversionEventService

router = APIRouter(prefix="/conversion-events", tags=["Conversion Events"])


def get_service(db: AsyncSession = Depends(get_db)) -> ConversionEventService:
    return ConversionEventService(ConversionEventRepository(db))


@router.post("", response_model=ConversionEventResponse, status_code=status.HTTP_201_CREATED)
async def record(payload: ConversionEventCreate, service: ConversionEventService = Depends(get_service)):
    return await service.record(payload)


@router.get("/product/{firestore_product_id}/funnel", response_model=FunnelResponse)
async def get_funnel(firestore_product_id: str, service: ConversionEventService = Depends(get_service)):
    return await service.get_funnel(firestore_product_id)


@router.get("/stats/overview", response_model=OverviewResponse)
async def get_overview(service: ConversionEventService = Depends(get_service)):
    return await service.get_overview()


@router.get("", response_model=list[ConversionEventResponse])
async def get_all(
    firestore_product_id: Optional[str] = Query(default=None),
    event_type: Optional[ConversionEventType] = Query(default=None),
    user_id: Optional[int] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    service: ConversionEventService = Depends(get_service),
):
    return await service.get_all(
        firestore_product_id=firestore_product_id,
        event_type=event_type,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )
