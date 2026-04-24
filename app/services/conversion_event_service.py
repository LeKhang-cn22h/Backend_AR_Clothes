from typing import Optional
from models.conversion_event import ConversionEvent, ConversionEventType
from repositories.conversion_event_repository import ConversionEventRepository
from schemas.conversion_event import ConversionEventCreate


class ConversionEventService:
    def __init__(self, repo: ConversionEventRepository):
        self.repo = repo

    async def record(self, data: ConversionEventCreate) -> ConversionEvent:
        return await self.repo.create(data)

    async def get_all(
        self,
        firestore_product_id: Optional[str] = None,
        event_type: Optional[ConversionEventType] = None,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ConversionEvent]:
        return await self.repo.get_all(
            firestore_product_id=firestore_product_id,
            event_type=event_type,
            user_id=user_id,
            skip=skip,
            limit=limit,
        )

    async def get_funnel(self, firestore_product_id: str) -> dict:
        return await self.repo.get_funnel(firestore_product_id)

    async def get_overview(self) -> dict:
        return await self.repo.get_overview()
