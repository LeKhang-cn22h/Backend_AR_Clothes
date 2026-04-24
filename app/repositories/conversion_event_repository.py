from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.conversion_event import ConversionEvent, ConversionEventType
from schemas.conversion_event import ConversionEventCreate


class ConversionEventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ConversionEventCreate) -> ConversionEvent:
        event = ConversionEvent(**data.model_dump())
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_by_id(self, id: int) -> Optional[ConversionEvent]:
        result = await self.db.execute(
            select(ConversionEvent).where(ConversionEvent.id == id, ConversionEvent.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        firestore_product_id: Optional[str] = None,
        event_type: Optional[ConversionEventType] = None,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ConversionEvent]:
        query = select(ConversionEvent).where(ConversionEvent.is_deleted == False)
        if firestore_product_id:
            query = query.where(ConversionEvent.firestore_product_id == firestore_product_id)
        if event_type:
            query = query.where(ConversionEvent.event_type == event_type)
        if user_id is not None:
            query = query.where(ConversionEvent.user_id == user_id)
        query = query.offset(skip).limit(limit).order_by(ConversionEvent.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_funnel(self, firestore_product_id: str) -> dict:
        query = (
            select(ConversionEvent.event_type, func.count(ConversionEvent.id))
            .where(
                ConversionEvent.firestore_product_id == firestore_product_id,
                ConversionEvent.is_deleted == False,
            )
            .group_by(ConversionEvent.event_type)
        )
        result = await self.db.execute(query)
        counts = {row[0].value: row[1] for row in result.all()}
        view = counts.get("view", 0)
        ar_try_on = counts.get("ar_try_on", 0)
        add_to_cart = counts.get("add_to_cart", 0)
        purchase = counts.get("purchase", 0)
        ar_to_purchase_rate = round(purchase / ar_try_on * 100, 2) if ar_try_on > 0 else 0.0
        return {
            "view": view,
            "ar_try_on": ar_try_on,
            "add_to_cart": add_to_cart,
            "purchase": purchase,
            "ar_to_purchase_rate": ar_to_purchase_rate,
        }

    async def get_overview(self) -> dict:
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        query = (
            select(ConversionEvent.event_type, func.count(ConversionEvent.id))
            .where(
                ConversionEvent.created_at >= thirty_days_ago,
                ConversionEvent.is_deleted == False,
            )
            .group_by(ConversionEvent.event_type)
        )
        result = await self.db.execute(query)
        counts = {row[0].value: row[1] for row in result.all()}
        return {
            "view": counts.get("view", 0),
            "ar_try_on": counts.get("ar_try_on", 0),
            "add_to_cart": counts.get("add_to_cart", 0),
            "purchase": counts.get("purchase", 0),
        }

    async def delete(self, id: int) -> bool:
        event = await self.get_by_id(id)
        if not event:
            return False
        event.is_deleted = True
        await self.db.commit()
        return True

    async def count(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ConversionEvent).where(ConversionEvent.is_deleted == False)
        )
        return result.scalar_one()

    async def update(self, id: int, **kwargs) -> Optional[ConversionEvent]:
        event = await self.get_by_id(id)
        if not event:
            return None
        for field, value in kwargs.items():
            setattr(event, field, value)
        await self.db.commit()
        await self.db.refresh(event)
        return event
