from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.garment import Garment


class GarmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, id: int) -> Optional[Garment]:
        result = await self.db.execute(select(Garment).where(Garment.id == id))
        return result.scalar_one_or_none()
